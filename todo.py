from flask import render_template, request, flash, redirect, url_for
from extensions import app
from database import get_db
from login import login_required


@app.route('/todo', methods=['GET', 'POST'])
@login_required
def todo():
    conn = get_db()

    if request.method == 'POST':
        action = request.form.get('action')
        list_type = request.form.get('list_type')
        todo_id = request.form.get('todo_id')
        content = request.form.get('content', '').strip()

        if action == 'add' and content and list_type in ['ticker', 'todo']:
            if list_type == 'ticker':
                content = content.upper()
            conn.execute('INSERT INTO todos1 (list_type, content) VALUES (?, ?)', (list_type, content))

        elif action == 'edit' and todo_id and content:
            conn.execute('UPDATE todos1 SET content=? WHERE id=?', (content, todo_id))

        elif action == 'delete' and todo_id:
            conn.execute('DELETE FROM todos1 WHERE id=?', (todo_id,))

        elif action == 'toggle' and todo_id:
            todo = conn.execute('SELECT completed FROM todos1 WHERE id=?', (todo_id,)).fetchone()
            if todo:
                new_status = 0 if todo['completed'] else 1
                conn.execute('UPDATE todos1 SET completed=? WHERE id=?', (new_status, todo_id))

        conn.commit()
        conn.close()

        # THIS IS THE KEY LINE:
        return redirect(url_for('todo'))  # Redirect after ANY POST!

    # Only runs on GET requests (initial load or after redirect)
    tickers = conn.execute('SELECT * FROM todos1 WHERE list_type="ticker" ORDER BY id').fetchall()
    todos = conn.execute('SELECT * FROM todos1 WHERE list_type="todo" ORDER BY id').fetchall()

    return render_template('todo.html', tickers=tickers, todos=todos)
