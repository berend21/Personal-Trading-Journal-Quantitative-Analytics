from flask import render_template, request, flash, redirect, url_for
from extensions import app
from database import get_db
from login import login_required

NOTE_COLORS = {
    '#fff475',
    '#fbbc04',
    '#ccff90',
    '#a7ffeb',
    '#cbf0f8',
    '#aecbfa',
    '#d7aefb',
    '#fdcfe8',
    '#e6c9a8',
    '#e8eaed',
    '#ffffff',
}

DEFAULT_NOTE_COLOR = '#fff475'
MAX_TITLE_LENGTH = 200
MAX_CONTENT_LENGTH = 100_000

def validate_color(color):
    if color in NOTE_COLORS:
        return color

    return DEFAULT_NOTE_COLOR

def get_note_id(form):
    note_id = form.get('id')

    try:
        return int(note_id)
    except (TypeError, ValueError):
        raise ValueError('Invalid note ID.')


def create_note(conn, form):
    title = form.get('title', '').strip()
    content = form.get('content', '').strip()
    color = validate_color(form.get('color', DEFAULT_NOTE_COLOR))

    if not content:
        raise ValueError('Note content cannot be empty.')

    if len(title) > MAX_TITLE_LENGTH:
        raise ValueError(f'Note title cannot exceed {MAX_TITLE_LENGTH} characters.')

    if len(content) > MAX_CONTENT_LENGTH:
        raise ValueError(f'Note content cannot exceed {MAX_CONTENT_LENGTH:,} characters.')

    conn.execute(
        '''
        INSERT INTO notes1 (title, content, color)
        VALUES (?, ?, ?)
        ''',
        (title, content, color)
    )

    conn.commit()


def update_note(conn, form):
    note_id = get_note_id(form)
    title = form.get('title', '').strip()
    content = form.get('content', '').strip()
    color = validate_color(form.get('color', DEFAULT_NOTE_COLOR))

    if not content:
        raise ValueError('Note content cannot be empty.')

    if len(title) > MAX_TITLE_LENGTH:
        raise ValueError(
            f'Note title cannot exceed {MAX_TITLE_LENGTH} characters.'
        )

    if len(content) > MAX_CONTENT_LENGTH:
        raise ValueError(
            f'Note content cannot exceed {MAX_CONTENT_LENGTH:,} characters.'
        )

    cursor = conn.execute(
        '''
        UPDATE notes1
        SET title=?,
            content=?,
            color=?,
            updated_at=CURRENT_TIMESTAMP
        WHERE id=?
        ''',
        (title, content, color, note_id)
    )

    if cursor.rowcount == 0:
        raise ValueError('Note not found.')

    conn.commit()



def delete_note(conn, form):
    note_id = get_note_id(form)

    cursor = conn.execute(
        'DELETE FROM notes1 WHERE id=?',
        (note_id,)
    )

    if cursor.rowcount == 0:
        raise ValueError('Note not found.')

    conn.commit()



def toggle_pin(conn, form):
    note_id = get_note_id(form)
    current_pinned = form.get('pinned')

    if current_pinned not in ('0', '1'):
        raise ValueError('Invalid pinned value.')

    pinned = 1 - int(current_pinned)

    cursor = conn.execute(
        '''
        UPDATE notes1
        SET pinned=?
        WHERE id=?
        ''',
        (pinned, note_id)
    )

    if cursor.rowcount == 0:
        raise ValueError('Note not found.')

    conn.commit()


def get_notes(conn, search=''):
    if search:
        search_param = f'%{search}%'

        return conn.execute(
            '''
            SELECT *
            FROM notes1
            WHERE title LIKE ?
               OR content LIKE ?
            ORDER BY pinned DESC, updated_at DESC
            ''',
            (search_param, search_param)
        ).fetchall()

    return conn.execute(
        '''
        SELECT *
        FROM notes1
        ORDER BY pinned DESC, updated_at DESC
        '''
    ).fetchall()


@app.route('/notes', methods=['GET', 'POST'])
@login_required
def notes():
    conn = get_db()

    if request.method == 'POST':
        action = request.form.get('action')

        try:
            if action == 'create':
                create_note(conn, request.form)
                flash('Note created!', 'success')

            elif action == 'edit':
                update_note(conn, request.form)
                flash('Note updated!', 'success')

            elif action == 'delete':
                delete_note(conn, request.form)
                flash('Note deleted!', 'success')

            elif action == 'pin':
                toggle_pin(conn, request.form)

            else:
                flash('Invalid note action.', 'error')

        except ValueError as e:
            flash(str(e), 'error')
        return redirect(
            url_for(
                'notes',
                search=request.form.get('search', '')
            )
        )

    search = request.args.get('search', '').strip()

    notes_list = get_notes(conn, search)

    pinned_notes = [
        note for note in notes_list
        if note['pinned']
    ]

    other_notes = [
        note for note in notes_list
        if not note['pinned']
    ]

    return render_template(
        'notes.html',
        pinned_notes=pinned_notes,
        other_notes=other_notes,
        search=search
    )
