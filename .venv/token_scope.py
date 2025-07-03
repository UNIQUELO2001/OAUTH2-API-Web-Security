import requests

'''input your current token here'''
ACCESS_TOKEN = "ya29.a0AS3H6NzHhiPpbB5Z5SbUzR1DjDJgzMZENHv_0TDUiXotSGQp2DlwPFxjMEiVapw-Zr08tCxV9Fs3cVLSAVev2ydzaNSBb7doS8MGi6G8R-EkJ8i10ilZLxoqDqryocGy5RPIZIy7DwRi1p9DqWAdCnKjO6Otx93gwzi32xSqaCgYKAaYSARcSFQHGX2MinV5wQxj2ewoafRn4CxlIQQ0175"
def check_token_scope():
    url = "https://www.googleapis.com/oauth2/v3/tokeninfo"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    response = requests.get(url, headers=headers)
    print("\n🔍 Token Info (JSON):", response.json())


# ✅ Run the function
if __name__ == "__main__":
    check_token_scope()
