from ollama import Client


class ImageNameGenerator:
    def __init__(self, model: str = "llava:7b", max_token: int = 30):
        self.client = Client(host="http://0.0.0.0:11434")
        self.model = model
        self.max_token = max_token

    def generate_name(
        self, image_path: str, model: str | None = None, max_token: int | None = None
    ):
        response = self.client.chat(
            model=model or self.model,
            messages=[
                {
                    "role": "user",
                    "content": "give a valid name to this image, max length of name should be 30 characters long"
                    "do not include quotes around the name. The name must not contain any special characters."
                    "do not include extension in the name and make sure the name is in snake_case"
                    "for example, if the image is a picture of a cat, the name should be cat_picture",
                    "images": [image_path],
                    "max_token": max_token or self.max_token,
                },
            ],
        )
        return response["message"]["content"]
