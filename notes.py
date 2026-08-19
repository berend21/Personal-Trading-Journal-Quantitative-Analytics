from flask import render_template, request, flash, redirect, url_for
from extensions import app
from database import get_db
from login import login_required



@app.route('/notes', methods=['GET', 'POST'])
@login_required
def notes():
    conn = get_db()
    
    if request.method == 'POST':
        action = request.form.get('action')
        note_id = request.form.get('id')
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        color = request.form.get('color', 'yellow')

        if action == 'create' and content:
            conn.execute('INSERT INTO notes1 (title, content, color) VALUES (?, ?, ?)',
                         (title, content, color))
            conn.commit()
            flash('Note created!', 'success')
            
        elif action == 'edit' and note_id and content:
            conn.execute('UPDATE notes1 SET title=?, content=?, color=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
                         (title, content, color, note_id))
            conn.commit()
            flash('Note updated!', 'success')
            
        elif action == 'delete' and note_id:
            conn.execute('DELETE FROM notes1 WHERE id=?', (note_id,))
            conn.commit()
            flash('Note deleted!', 'success')
            
        elif action == 'pin' and note_id:
            pinned = 1 if request.form.get('pinned') == '0' else 0
            conn.execute('UPDATE notes1 SET pinned=? WHERE id=?', (pinned, note_id))
            conn.commit()

    search = request.args.get('search', '').strip()
    search_condition = ''
    params = []
    if search:
        search_condition = 'WHERE (title LIKE ? OR content LIKE ?)'
        search_param = f'%{search}%'
        params = [search_param, search_param]

    notes_list = conn.execute(f'''
        SELECT * FROM notes1 
        {search_condition}
        ORDER BY pinned DESC, updated_at DESC
    ''', params).fetchall()
     

    pinned_notes = [note for note in notes_list if note['pinned']]
    other_notes = [note for note in notes_list if not note['pinned']]

    return render_template('notes.html', pinned_notes=pinned_notes, other_notes=other_notes, search=search)
