import json

def migrate_gallery_table(conn):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'gallery'
    """)

    if not cursor.fetchone():
        print("Gallery table does not exist yet. Skipping migration.")
        return

    cursor.execute("SELECT id, image_path FROM gallery")
    rows = cursor.fetchall()

    updated = False

    for row in rows:
        row_id = row["id"]
        image_path = row["image_path"]

        if not image_path:
            continue

        try:
            parsed = json.loads(image_path)

            if not (
                isinstance(parsed, list)
                and all(isinstance(item, str) for item in parsed)
            ):
                raise ValueError("Invalid gallery image list")

        except (json.JSONDecodeError, TypeError, ValueError):
            cursor.execute(
                "UPDATE gallery SET image_path = ? WHERE id = ?",
                (json.dumps([image_path]), row_id)
            )
            updated = True

    if updated:
        print("Gallery table migrated to support multi-images in image_path.")
    else:
        print("Gallery image paths already use valid JSON string lists.")
