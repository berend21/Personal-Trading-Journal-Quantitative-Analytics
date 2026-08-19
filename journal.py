from flask import render_template, request, flash, redirect, url_for
from database import get_db
from datetime import datetime, timedelta, date
from login import login_required
from extensions import app
import calendar


@app.route('/journal', methods=['GET', 'POST'])
@app.route('/journal/<date_str>', methods=['GET', 'POST'])
@login_required
def journal(date_str=None):

    if request.method == 'POST':
        date_str = request.form.get('date')
        entry_type = request.form.get('entry_type')
        content = request.form.get('content', '').strip()
        #print(f"Form data - date: {date_str}, type: {entry_type}, content length: {len(content)}")
        
        try:
            journal_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            if entry_type == 'weekly':
                week_start = journal_date - timedelta(days=journal_date.weekday())

            elif entry_type == 'monthly':
                month_start = journal_date.replace(day=1)
            else:
                week_start = None
                month_start = None 
        except ValueError:
            flash('Invalid date format', 'error')
            return redirect(url_for('journal'))
        
        conn = get_db()
        
        try:
            if entry_type == 'daily':
                existing = conn.execute("""
                    SELECT id FROM journal_entries 
                    WHERE date = ? AND entry_type = 'daily'
                """, (date_str,)).fetchone()
            elif entry_type == 'weekly':  
                existing = conn.execute("""
                    SELECT id FROM journal_entries 
                    WHERE week_start_date = ? AND entry_type = 'weekly'
                """, (week_start.isoformat(),)).fetchone()

            elif entry_type == 'monthly':
                existing = conn.execute("""
                    SELECT id FROM journal_entries 
                    WHERE month_start_date = ? AND entry_type = 'monthly'
                """, (month_start.isoformat(),)).fetchone()
            
            if existing:
                conn.execute("""
                    UPDATE journal_entries 
                    SET content = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (content, existing['id']))

            else:
                if entry_type == 'daily':
                    conn.execute("""
                        INSERT INTO journal_entries (date, entry_type, content) 
                        VALUES (?, ?, ?)
                    """, (date_str, entry_type, content))
                elif entry_type == 'weekly':  
                    conn.execute("""
                        INSERT INTO journal_entries (date, entry_type, content, week_start_date) 
                        VALUES (?, ?, ?, ?)
                    """, (date_str, entry_type, content, week_start.isoformat()))
                elif entry_type == 'monthly':
                    conn.execute("""
                        INSERT INTO journal_entries (date, entry_type, content, month_start_date) 
                        VALUES (?, ?, ?, ?)
                    """, (date_str, entry_type, content, month_start.isoformat()))

            
            conn.commit()
            flash(f'{entry_type.title()} journal saved!', 'success')
        except Exception as e:
            print(f"Database error: {e}")
            flash('Error saving journal entry', 'error')

             
        
        return redirect(url_for('journal', date_str=date_str))
    
    if date_str:
        #print(f"Showing daily view for {date_str}")
        try:
            journal_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            week_start = journal_date - timedelta(days=journal_date.weekday())
            month_start = journal_date.replace(day=1)  
        except ValueError:
            flash('Invalid date format', 'error')
            return redirect(url_for('journal'))
        
 


        year_month = journal_date.strftime('%Y-%m')
        start_of_month = f"{year_month}-01"
        last_day = calendar.monthrange(journal_date.year, journal_date.month)[1]
        end_of_month = f"{year_month}-{last_day:02d}"

        # This will be cached for 32 different months → basically instant after first load
        conn = get_db()
        all_month_trades = conn.execute("""
            SELECT *, DATE(open_time) as trade_date
            FROM trades
            WHERE parent_id IS NULL
            AND open_time BETWEEN ? AND ?
            ORDER BY open_time DESC
        """, (start_of_month + " 00:00:00", end_of_month + " 23:59:59")).fetchall()
        # Filter only today's parent trades
        trades = [t for t in all_month_trades if t['trade_date'] == date_str]

        # Keep the journal entries queries exactly as they are (they're already fast)
        conn = get_db()
        
        daily_entry = conn.execute("""
            SELECT * FROM journal_entries 
            WHERE date = ? AND entry_type = 'daily'
        """, (date_str,)).fetchone()
        
        weekly_entry = conn.execute("""
            SELECT * FROM journal_entries 
            WHERE week_start_date = ? AND entry_type = 'weekly'
        """, (week_start.isoformat(),)).fetchone()

        monthly_entry = conn.execute("""
            SELECT * FROM journal_entries 
            WHERE month_start_date = ? AND entry_type = 'monthly'
        """, (month_start.isoformat(),)).fetchone()
        
         
        
        return render_template('daily_journal.html',
                             date=journal_date,
                             date_str=date_str,
                             week_start=week_start,
                             trades=trades,
                             daily_entry=daily_entry,
                             weekly_entry=weekly_entry,
                             monthly_entry=monthly_entry)
    

    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))

    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    

    conn = get_db()

    trades_query = f"""
        SELECT DATE(open_time) as trade_date, COUNT(*) as trade_count,
               SUM(CASE WHEN RR > 0 THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN RR < 0 THEN 1 ELSE 0 END) as losses
        FROM trades
        WHERE parent_id IS NULL 
        AND strftime('%Y-%m', open_time) = ?
        GROUP BY DATE(open_time)
    """
    trades_data = {}
    for row in conn.execute(trades_query, (f"{year:04d}-{month:02d}",)):
        trades_data[row['trade_date']] = {
            'count': row['trade_count'],
            'wins': row['wins'],
            'losses': row['losses']
        }

    journal_query = """
        SELECT date, entry_type, 
               CASE WHEN LENGTH(content) > 0 THEN 1 ELSE 0 END as has_content
        FROM journal_entries 
        WHERE strftime('%Y-%m', date) = ?
    """
    journal_data = {}
    for row in conn.execute(journal_query, (f"{year:04d}-{month:02d}",)):
        date_str_loop = row['date']
        if date_str_loop not in journal_data:
            journal_data[date_str_loop] = {}
        journal_data[date_str_loop][row['entry_type']] = row['has_content']
    

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    return render_template('journal.html', 
                         calendar_data=cal,
                         year=year, 
                         month=month,
                         month_name=month_name,
                         trades_data=trades_data,
                         journal_data=journal_data,
                         prev_year=prev_year,
                         prev_month=prev_month,
                         next_year=next_year,
                         next_month=next_month,
                         today=date.today().isoformat())
