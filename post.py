class Post:
    """
    A class to represent a blog post

    Attributes:
        id (int): The unique identifier of the post
        title (str): The title of the blog post
        subtitle (str): The subtitle or description of the blog post
        body (str): The main content of the blog post
    """

    def __init__(self, post_id, title, subtitle, body, image_url):
        self.id = post_id
        self.title = title
        self.subtitle = subtitle
        self.body = body
        self.image_url = image_url