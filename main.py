from ollama import Client

client = Client(
    host="http://0.0.0.0:11435",
)


def ai_image_name(image_path):
    response = client.chat(
        model="llava:7b",
        messages=[
            {
                "role": "user",
                "content": "give a valid name to this image, max length of name should be 30 characters long" \
                        "do not include quotes around the name. The name must not contain any special characters." \
                        "do not include extension in the name and make sure the name is in snake_case" \
                        "for example, if the image is a picture of a cat, the name should be cat_picture",
                "images": [image_path],
                "max_token": 30,
            },
        ],
    )
    return response["message"]["content"]


image_paths = ["./1.png", "./2.png", "./3.png"]

for image_path in image_paths:
    print(ai_image_name(image_path))
