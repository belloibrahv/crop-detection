"""
kaggle_login.py — Interactive Kaggle OAuth login.
Run once to authenticate: ml/.venv/bin/python ml/kaggle_login.py
"""
import kagglehub
print("Opening browser for Kaggle OAuth login...")
print("Sign in with your Kaggle account when the browser opens.")
kagglehub.login()
print("\nLogin successful! Credentials cached. You can now run download_all.py")
