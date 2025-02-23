import random
import string
import requests
import concurrent.futures

BASE_URL = "http://localhost:8000/api"


def generate_random_string(length=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))


def register_user(email, username, password="securepassword123"):
    payload = {
        "email": email,
        "username": username,
        "password": password
    }
    try:
        response = requests.post(f"{BASE_URL}/register/", json=payload)
        print(f"[REGISTER] Username: {username} | Email: {email} | Status: {response.status_code}")
        print("Response:", response.text)
        return response
    except Exception as e:
        print(f"[REGISTER] Error: {e}")
        return None


def verify_email(user_id, code):
    payload = {"user_id": user_id, "code": code}
    try:
        response = requests.post(f"{BASE_URL}/verify-email/", json=payload)
        print(f"[VERIFY EMAIL] User ID: {user_id} | Code: {code} | Status: {response.status_code}")
        print("Response:", response.text)
        return response
    except Exception as e:
        print(f"[VERIFY EMAIL] Error: {e}")
        return None


def login_user(email, password="securepassword123"):
    payload = {"email": email, "password": password}
    try:
        response = requests.post(f"{BASE_URL}/login/", json=payload)
        print(f"[LOGIN] Email: {email} | Status: {response.status_code}")
        print("Response:", response.text)
        return response
    except Exception as e:
        print(f"[LOGIN] Error: {e}")
        return None


def request_password_reset(email):
    payload = {"email": email}
    try:
        response = requests.post(f"{BASE_URL}/password-reset/", json=payload)
        print(f"[PASSWORD RESET REQUEST] Email: {email} | Status: {response.status_code}")
        print("Response:", response.text)
        try:
            data = response.json()
            token = data.get("reset_token")
            if token:
                print("[PASSWORD RESET REQUEST] Token extracted from response.")
            else:
                token = None
                print("[PASSWORD RESET REQUEST] No token found in response.")
        except Exception:
            token = None
            print("[PASSWORD RESET REQUEST] Could not parse JSON.")
        return token
    except Exception as e:
        print(f"[PASSWORD RESET REQUEST] Error: {e}")
        return None


def confirm_password_reset(token, new_password="newsecurepassword123"):
    payload = {"token": token, "new_password": new_password}
    try:
        response = requests.post(f"{BASE_URL}/password-reset/confirm/", json=payload)
        print(f"[PASSWORD RESET CONFIRM] Token: {token} | Status: {response.status_code}")
        print("Response:", response.text)
        return response
    except Exception as e:
        print(f"[PASSWORD RESET CONFIRM] Error: {e}")
        return None


def process_user(user_index):
    # Generate a random username and email address.
    username = generate_random_string(8)
    email = f"{generate_random_string(5)}@example.com"
    print(f"===== Processing user {user_index + 1} =====")

    # 1. Register the user.
    reg_response = register_user(email, username)
    if not reg_response:
        print(f"[MAIN] Registration error for user {user_index + 1}.")
        return

    try:
        data = reg_response.json()
        user_id = data.get("user_id")
        # Get verification code from response (API must return it in testing mode)
        verification_code = data.get("verification_code")
    except Exception as e:
        print(f"[MAIN] Could not parse registration response for user {user_index + 1}: {e}")
        return

    if not user_id or not verification_code:
        print(f"[MAIN] Missing user_id or verification_code for user {user_index + 1}.")
        return

    # 2. Verify email using the actual code.
    verify_response = verify_email(user_id, verification_code)
    if not verify_response or verify_response.status_code != 200:
        print(f"[MAIN] Email verification failed for user {user_index + 1}.")
        return

    # 3. Login with the registered credentials.
    login_response = login_user(email)
    if not login_response or login_response.status_code != 200:
        print(f"[MAIN] Login failed for user {user_index + 1}.")
        return

    # 4. Request a password reset.
    reset_token = request_password_reset(email)
    if not reset_token:
        print(f"[MAIN] Password reset token not available for user {user_index + 1}.")
        return

    # 5. Confirm the password reset.
    confirm_password_reset(reset_token)
    print(f"===== Completed user {user_index + 1} =====\n")


def main():
    total_users = 100_000
    max_workers = 10  # run 10 tasks concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all user flows concurrently (the executor will run 10 at a time)
        futures = [executor.submit(process_user, i) for i in range(total_users)]
        # Optionally, wait for all futures to complete:
        concurrent.futures.wait(futures)


if __name__ == "__main__":
    main()
