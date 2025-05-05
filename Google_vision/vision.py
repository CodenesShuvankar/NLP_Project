from openai import OpenAI

client = OpenAI(
    api_key="AIzaSyCOpY-QQij2ciHFJ5ZM036FhiE8zkgm3_E",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)
def summarize(text):
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        n=1,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": f"Summarize this text point wise {text}"
            }
        ]
    )

    return response.choices[0].message.content

# print(summarize("shuvanakr , 711401 amta pitambar high school pass 2018 pin "))