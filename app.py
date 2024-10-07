import streamlit as st
from streamlit_option_menu import option_menu
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import altair as alt

# Database Functions
def create_tasktable():
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT,
            task TEXT
        )
    ''')
    conn.commit()

def add_task(day, task):
    c.execute('INSERT INTO tasks(day, task) VALUES (?, ?)', (day, task))
    conn.commit()

def get_tasks(day):
    c.execute('SELECT id, task FROM tasks WHERE day = ?', (day,))
    return c.fetchall()

def delete_task(task_id):
    c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()

def create_progresstable():
    c.execute('''
        CREATE TABLE IF NOT EXISTS progress(
            date TEXT,
            task_id INTEGER,
            completed BOOLEAN,
            PRIMARY KEY (date, task_id),
            FOREIGN KEY(task_id) REFERENCES tasks(id)
        )
    ''')
    conn.commit()

def update_progress(date, task_id, completed):
    c.execute('''
        INSERT OR REPLACE INTO progress(date, task_id, completed)
        VALUES (?, ?, ?)
    ''', (date, task_id, int(completed)))
    conn.commit()

def get_progress(date):
    c.execute('SELECT task_id, completed FROM progress WHERE date = ?', (date,))
    progress_data = c.fetchall()
    return {task_id: bool(completed) for task_id, completed in progress_data}

def reset_progress(date):
    c.execute('DELETE FROM progress WHERE date = ?', (date,))
    conn.commit()

def reset_all_progress():
    c.execute('DELETE FROM progress')
    conn.commit()

def get_all_progress():
    c.execute('SELECT * FROM progress')
    return c.fetchall()

def get_weekly_progress():
    # Get all unique dates from the progress table, in order
    c.execute('SELECT DISTINCT date FROM progress ORDER BY date')
    dates = c.fetchall()

    progress_data = []

    for date_tuple in dates:
        date_str = date_tuple[0]
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        day_name = date_obj.strftime('%A')

        # Get total tasks assigned for that day of the week
        total_tasks = len(get_tasks(day_name))

        # Get the number of tasks completed on that date
        c.execute('SELECT COUNT(*) FROM progress WHERE date = ? AND completed = 1', (date_str,))
        completed_tasks = c.fetchone()[0]

        # Calculate percentage
        if total_tasks > 0:
            percentage = (completed_tasks / total_tasks) * 100
        else:
            percentage = 0

        progress_data.append((date_str, percentage))

    # Sort the data by date
    progress_data.sort(key=lambda x: x[0])
    return progress_data

# New Functions for Insights
def calculate_statistics():
    # Get all progress data
    c.execute('SELECT date, completed FROM progress')
    data = c.fetchall()
    if not data:
        return None

    df = pd.DataFrame(data, columns=['Date', 'Completed'])
    df['Date'] = pd.to_datetime(df['Date'])
    df['Completed'] = df['Completed'].astype(int)

    # Total tasks and completed tasks
    total_tasks = len(df)
    completed_tasks = df['Completed'].sum()

    # Overall completion rate
    overall_completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0

    # Daily completion rates
    daily_stats = df.groupby('Date').agg({'Completed': ['sum', 'count']})
    daily_stats.columns = ['Completed_Tasks', 'Total_Tasks']
    daily_stats['Daily_Completion_Rate'] = (daily_stats['Completed_Tasks'] / daily_stats['Total_Tasks']) * 100

    # Weekly completion rates
    df['Week'] = df['Date'].dt.isocalendar().week.astype(int)  # Convert to int
    weekly_stats = df.groupby('Week').agg({'Completed': ['sum', 'count']})
    weekly_stats.columns = ['Completed_Tasks', 'Total_Tasks']
    weekly_stats['Weekly_Completion_Rate'] = (weekly_stats['Completed_Tasks'] / weekly_stats['Total_Tasks']) * 100

    # Day-wise performance
    df['Day_Name'] = df['Date'].dt.day_name()
    daywise_stats = df.groupby('Day_Name').agg({'Completed': ['sum', 'count']})
    daywise_stats.columns = ['Completed_Tasks', 'Total_Tasks']
    daywise_stats['Daywise_Completion_Rate'] = (daywise_stats['Completed_Tasks'] / daywise_stats['Total_Tasks']) * 100
    daywise_stats = daywise_stats.reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])

    # Prepare data for heatmap (optional)
    heatmap_data = df.groupby(['Date', 'Day_Name']).agg({'Completed': ['sum', 'count']})
    heatmap_data.columns = ['Completed_Tasks', 'Total_Tasks']
    heatmap_data.reset_index(inplace=True)

    return {
        'overall': {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'completion_rate': overall_completion_rate
        },
        'daily': daily_stats.reset_index(),
        'weekly': weekly_stats.reset_index(),
        'daywise': daywise_stats.reset_index(),
        'heatmap': heatmap_data
    }

def motivational_message(completion_rate):
    if completion_rate == 100:
        return "Excellent work! You've completed all your tasks. Keep up the great discipline!"
    elif completion_rate >= 80:
        return "Great job! You're on track. Aim for 100% tomorrow!"
    elif completion_rate >= 50:
        return "Good effort! Try to push a bit more for better results."
    else:
        return "Don't give up! Identify obstacles and strive to improve your completion rate."

def show_insights():
    st.header("Personal Insights Dashboard")

    stats = calculate_statistics()

    if not stats:
        st.info("No progress data available. Complete some tasks to see insights.")
        return

    overall = stats['overall']
    daily = stats['daily']
    weekly = stats['weekly']
    daywise = stats['daywise']
    heatmap_data = stats['heatmap']

    # Display Overall Statistics
    st.subheader("Overall Statistics")
    st.write(f"**Total Tasks:** {overall['total_tasks']}")
    st.write(f"**Total Completed Tasks:** {overall['completed_tasks']}")
    st.write(f"**Overall Completion Rate:** {overall['completion_rate']:.2f}%")

    # Motivational Message
    message = motivational_message(overall['completion_rate'])
    st.info(message)

    # Create a 2x2 grid
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    # Completion Rate Over Time (Line Chart)
    with col1:
        st.subheader("Completion Rate Over Time")
        line_chart = alt.Chart(daily).mark_line(point=True).encode(
            x='Date:T',
            y=alt.Y('Daily_Completion_Rate:Q', scale=alt.Scale(domain=[0, 100])),
            tooltip=['Date', 'Daily_Completion_Rate']
        ).properties(
            width=350,
            height=300
        )
        st.altair_chart(line_chart, use_container_width=False)

    # Weekly Completion Rate (Bar Chart)
    with col2:
        st.subheader("Weekly Completion Rate")
        bar_chart = alt.Chart(weekly).mark_bar().encode(
            x='Week:N',
            y=alt.Y('Weekly_Completion_Rate:Q', scale=alt.Scale(domain=[0, 100])),
            tooltip=['Week', 'Weekly_Completion_Rate']
        ).properties(
            width=350,
            height=300
        )
        st.altair_chart(bar_chart, use_container_width=False)

    # Day-wise Performance (Bar Chart)
    with col3:
        st.subheader("Day-wise Performance")
        day_bar_chart = alt.Chart(daywise).mark_bar().encode(
            x=alt.X('Day_Name:N', sort=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']),
            y=alt.Y('Daywise_Completion_Rate:Q', scale=alt.Scale(domain=[0, 100])),
            tooltip=['Day_Name', 'Daywise_Completion_Rate']
        ).properties(
            width=350,
            height=300
        )
        st.altair_chart(day_bar_chart, use_container_width=False)

    # Task Completion Heatmap
    with col4:
        st.subheader("Task Completion Heatmap")
        heatmap_chart = alt.Chart(heatmap_data).mark_rect().encode(
            x=alt.X('Day_Name:N', sort=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']),
            y='Date:T',
            color=alt.Color('Completed_Tasks:Q', scale=alt.Scale(scheme='greens')),
            tooltip=['Date', 'Day_Name', 'Completed_Tasks', 'Total_Tasks']
        ).properties(
            width=350,
            height=300
        )
        st.altair_chart(heatmap_chart, use_container_width=False)

    # Frequently Incomplete Tasks
    st.subheader("Frequently Incomplete Tasks")
    c.execute('''
        SELECT tasks.task, COUNT(*) as incomplete_count
        FROM progress
        JOIN tasks ON progress.task_id = tasks.id
        WHERE progress.completed = 0
        GROUP BY tasks.task
        ORDER BY incomplete_count DESC
        LIMIT 5
    ''')
    incomplete_tasks = c.fetchall()
    if incomplete_tasks:
        df_incomplete = pd.DataFrame(incomplete_tasks, columns=['Task', 'Times Incomplete'])
        st.table(df_incomplete)
    else:
        st.write("All tasks are being completed! Great job!")

# Main App Functions
def main():
    # Page Config
    st.set_page_config(page_title="Daily Task Tracker", layout="wide")
    st.markdown("<style>" + open('styles.css').read() + "</style>", unsafe_allow_html=True)

    # Connect to Database
    global conn, c
    conn = sqlite3.connect('database.db', check_same_thread=False)
    c = conn.cursor()

    # Create Tables if they don't exist
    create_tasktable()
    create_progresstable()

    # Option Menu in Sidebar
    with st.sidebar:
        selected = option_menu(
            menu_title="Main Menu",
            options=["Today's Tasks", "Weekly Progress", "Insights", "Settings"],
            icons=["check2-circle", "bar-chart-line", "graph-up", "gear"],
            menu_icon="cast",
            default_index=0,
        )

    if selected == "Today's Tasks":
        show_today_tasks()
    elif selected == "Weekly Progress":
        show_weekly_progress()
    elif selected == "Insights":
        show_insights()
    elif selected == "Settings":
        show_settings()

def show_today_tasks():
    st.header("Today's Tasks")
    today = datetime.now()
    day_name = today.strftime('%A')
    date_str = today.strftime('%Y-%m-%d')

    tasks = get_tasks(day_name)
    progress = get_progress(date_str)

    st.write(f"**Tasks for {day_name}, {date_str}**")

    # Reset Today's Progress Button
    if st.button("Reset Today's Progress"):
        reset_progress(date_str)
        st.success("Today's progress has been reset.")
        st.rerun()

    total_tasks = len(tasks)

    if total_tasks > 0:
        updated_progress = {}
        for task_id, task in tasks:
            completed = progress.get(task_id, False)
            checkbox = st.checkbox(task, value=completed, key=f"{date_str}_{task_id}")
            updated_progress[task_id] = checkbox

        # Update progress in the database after collecting all checkbox states
        for task_id, completed in updated_progress.items():
            update_progress(date_str, task_id, completed)

        # Calculate completed tasks based on updated_progress
        completed_tasks = sum(1 for completed in updated_progress.values() if completed)

        progress_ratio = completed_tasks / total_tasks
        percentage_display = progress_ratio * 100
        st.write(f"**Progress:** {completed_tasks}/{total_tasks} tasks completed ({percentage_display:.2f}%).")
        st.progress(progress_ratio)
    else:
        st.info("No tasks assigned for today.")

def show_weekly_progress():
    st.header("Weekly Progress")
    data = get_weekly_progress()
    if data:
        df = pd.DataFrame(data, columns=['Date', 'Percentage'])
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')

        st.line_chart(df.set_index('Date')['Percentage'])
        st.table(df)
    else:
        st.info("No progress data available.")

def show_settings():
    st.header("Settings")
    st.subheader("Manage Your Tasks")

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    selected_day = st.selectbox("Select Day", days)

    st.subheader(f"Tasks for {selected_day}")
    tasks = get_tasks(selected_day)

    if tasks:
        for task_id, task in tasks:
            col1, col2 = st.columns([0.8, 0.2])
            col1.write(task)
            if col2.button("Delete", key=f"delete_{task_id}"):
                delete_task(task_id)
                st.success("Task deleted successfully.")
                st.rerun()
    else:
        st.info(f"No tasks for {selected_day}")

    st.subheader("Add New Task")
    new_task = st.text_input("Task Description", key='new_task')
    if st.button("Add Task"):
        if new_task.strip() != "":
            add_task(selected_day, new_task.strip())
            st.success("Task added successfully!")
            st.rerun()
        else:
            st.warning("Task description cannot be empty.")

    # Add Reset Progress Section in Settings
    st.subheader("Reset Completed Tasks for a Specific Date")
    reset_date = st.date_input("Select Date to Reset")
    if st.button("Reset Progress", key="reset_progress"):
        reset_date_str = reset_date.strftime('%Y-%m-%d')
        reset_progress(reset_date_str)
        st.success(f"Progress for {reset_date_str} has been reset.")

if __name__ == '__main__':
    main()
