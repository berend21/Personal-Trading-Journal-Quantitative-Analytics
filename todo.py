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
        try:
            priority = int(request.form.get('priority', 1))
        except (TypeError, ValueError):
            priority = 1

        if priority not in [0, 1, 2]:
            priority = 1

        if action == 'add' and content and list_type in ['ticker', 'todo']:
            if list_type == 'ticker':
                content = content.upper()
            conn.execute('INSERT INTO todos (list_type, content, priority) VALUES (?, ?, ?)', (list_type, content, priority))

        elif action == 'edit' and todo_id and content:
            if list_type == 'ticker':
                content = content.upper()
            conn.execute('UPDATE todos SET content=?, priority=? WHERE id=?', (content, priority, todo_id))

        elif action == 'delete' and todo_id:
            conn.execute('DELETE FROM todos WHERE id=?', (todo_id,))

        elif action == 'toggle' and todo_id:
            todo = conn.execute('SELECT completed FROM todos WHERE id=?', (todo_id,)).fetchone()
            if todo:
                new_status = 0 if todo['completed'] else 1
                conn.execute('UPDATE todos SET completed=? WHERE id=?', (new_status, todo_id))

        conn.commit()
        conn.close()


        return redirect(url_for('todo'))


    tickers = conn.execute('SELECT * FROM todos WHERE list_type="ticker" ORDER BY id').fetchall()
    todos = conn.execute('SELECT * FROM todos WHERE list_type="todo" ORDER BY id').fetchall()

    return render_template('todo.html', tickers=tickers, todos=todos)
