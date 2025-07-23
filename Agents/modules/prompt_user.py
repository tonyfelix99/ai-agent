def ask_user(_: str) -> str:
    confirmation = input("Do you want to continue? (yes/no): ").strip().lower()
    return "confirmed" if confirmation == "yes" else "cancelled"
