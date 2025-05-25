import sqlite3

def clear_database():
    conn = sqlite3.connect("matches.db")
    cursor = conn.cursor()

    # Usuń zawartość tabel
    cursor.execute("DELETE FROM players")
    cursor.execute("DELETE FROM matches")

    # Resetuj AUTOINCREMENT (opcjonalnie, ale zalecane)
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='players'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='matches'")

    conn.commit()
    conn.close()
    print("✅ Baza danych została wyczyszczona.")

if __name__ == "__main__":
    clear_database()
