import flask
import talisker

from canonicalwebteam import image_template
from canonicalwebteam.blog import (
    BlogViews,
    BlogAPI,
    build_blueprint,
    NotFoundError,
)
from requests.exceptions import RequestException

from webapp.helpers import get_yaml


def init_blog(app, url_prefix):
    blog_api = BlogAPI(session=talisker.requests.get_session())
    blog = build_blueprint(
        BlogViews(
            api=blog_api,
            blog_title="Snapcraft Blog",
            tag_ids=[2996],
            excluded_tags=[3184, 3265, 3408],
        )
    )

    @blog.route("/api/snap-posts/<snap>")
    def snap_posts(snap):
        try:
            blog_tags = blog_api.get_tag_by_name(f"sc:snap:{snap}")
        except NotFoundError:
            blog_tags = None

        blog_articles = None
        articles = []

        third_party_blogs = get_yaml("blog/content/blog-posts.yaml")

        if third_party_blogs and snap in third_party_blogs:
            post = third_party_blogs[snap]
            cdn_image = "/".join(
                [
                    "https://res.cloudinary.com",
                    "canonical",
                    "image",
                    "fetch",
                    "f_auto,q_auto,fl_sanitize,w_346,h_231,c_fill",
                    post["image"],
                ]
            )
            brand_image = "https://assets.ubuntu.com/v1/aae0f33a-omgubuntu.svg"
            image_element = "".join(
                [
                    f'<img src="{cdn_image}" ',
                    'style="display:block">',
                    f'<img src="{brand_image}" ',
                    'class="p-blog-post__source" />',
                ]
            )
            articles.append(
                {
                    "slug": post["uri"],
                    "title": post["title"],
                    "image": image_element,
                }
            )

        if blog_tags:
            snapcraft_tag = blog_api.get_tag_by_name("snapcraft.io")

            try:
                blog_articles, total_pages = blog_api.get_articles(
                    tags=blog_tags["id"],
                    tags_exclude=[3184, 3265, 3408],
                    per_page=3 - len(articles),
                )
            except RequestException:
                blog_articles = []

            for article in blog_articles:
                if article["image"]:
                    featured_media = image_template(
                        url=article["image"]["source_url"],
                        alt="",
                        width="346",
                        height="231",
                        fill=True,
                        hi_def=True,
                        loading="auto",
                    )
                else:
                    featured_media = None

                url = f"/blog/{article['slug']}"

                if snapcraft_tag["id"] not in article["tags"]:
                    url = f"https://ubuntu.com{url}"

                articles.append(
                    {
                        "slug": url,
                        "title": article["title"]["rendered"],
                        "image": featured_media,
                    }
                )

        return flask.jsonify(articles)

    @blog.route("/api/series/<series>")
    def snap_series(series):
        blog_articles = None
        articles = []

        try:
            blog_articles, total_pages = blog_api.get_articles(series)
        except RequestException:
            blog_articles = []

        for article in blog_articles:
            articles.append(
                {
                    "slug": article["slug"],
                    "title": article["title"]["rendered"],
                }
            )

        return flask.jsonify(articles)

    @blog.context_processor
    def add_newsletter():
        newsletter_subscribed = flask.request.args.get(
            "newsletter", default=False, type=bool
        )

        return {"newsletter_subscribed": newsletter_subscribed}

    app.register_blueprint(blog, url_prefix=url_prefix)
