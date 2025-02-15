from ollama import Client

client = Client(
    host="http://0.0.0.0:11435",
    #   headers={'x-some-header': 'some-value'}
)


def ai_image_name(image_path):
    response = client.chat(
        model="llava:7b",
        messages=[
            {
                "role": "user",
                "content": "give a valid name to this image, max length of name should be 30 characters long",
                "images": ["./1.png"],
                # 'images': ['./2.png']
                # 'images': ['./3.png']
            },
        ],
    )
    return response["message"]["content"]


image_paths = ["./1.png", "./2.png", "./3.png"]

for image_path in image_paths:
    print(ai_image_name(image_path))
