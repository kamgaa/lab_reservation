import streamlit as st
import pandas as pd
import sqlite3
#import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta, time
from streamlit_option_menu import option_menu
from config import PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR, BACKGROUND_COLOR, TEXT_COLOR, DATABASE_FILE
from database import add_user, check_user, init_db, update_user
from streamlit_modal import Modal

# 페이지 설정
st.set_page_config(page_title="실험실 예약 시스템", layout="wide")

# 데이터베이스 초기화
init_db()

# 데이터베이스 연결 함수
def get_connection():
    return sqlite3.connect(DATABASE_FILE)

# 예약 데이터 삽입 함수
def insert_reservation(student_id, start_time, end_time, reservation_date):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO reservations (student_id, start_time, end_time, reservation_date) VALUES (?, ?, ?, ?)",
              (student_id, start_time, end_time, reservation_date))
    conn.commit()
    conn.close()

# 예약 데이터 조회 함수
def get_reservations():
    conn = get_connection()
    df = pd.read_sql_query("SELECT reservations.*, users.name, users.team, users.team_color FROM reservations JOIN users ON reservations.student_id = users.student_id", conn)
    conn.close()
    return df

# 이번 주 예약된 시간을 계산하는 함수
def get_reserved_time(student_id):
    conn = get_connection()
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())  # 월요일
    end_of_week = start_of_week + timedelta(days=6)  # 일요일

    df = pd.read_sql_query(f"""
        SELECT * FROM reservations
        WHERE student_id = '{student_id}'
        AND reservation_date BETWEEN '{start_of_week}' AND '{end_of_week}'
    """, conn)

    total_reserved_time = 0
    for _, row in df.iterrows():
        start_time = datetime.strptime(row['start_time'], '%H:%M:%S').time()
        end_time = datetime.strptime(row['end_time'], '%H:%M:%S').time()
        reserved_hours = (datetime.combine(date.min, end_time) - datetime.combine(date.min, start_time)).seconds / 3600
        total_reserved_time += reserved_hours

    conn.close()
    return total_reserved_time

# 로그인 상태 초기화
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False
if 'register' not in st.session_state:
    st.session_state['register'] = False
if 'selected_date' not in st.session_state:
    st.session_state['selected_date'] = None
if 'student_id' not in st.session_state:
    st.session_state['student_id'] = None
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = None
if 'team' not in st.session_state:
    st.session_state['team'] = None
if 'team_color' not in st.session_state:
    st.session_state['team_color'] = None

# 미리 정해진 10개의 색상
color_palette = ['#FF5733', '#33FF57', '#3357FF', '#FF33A8', '#FF8C33', '#33FFF3', '#FF33D4', '#D433FF', '#33FF88', '#33A8FF']

# 로그인 페이지
def login_page():
    st.title("로그인 페이지")
    student_id = st.text_input("학번 (8자리 숫자)")
    password = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        user = check_user(student_id, password)
        if user:
            st.session_state['logged_in'] = True
            st.session_state['student_id'] = user[1]  # student_id
            st.session_state['user_name'] = user[2]  # name
            st.session_state['team'] = user[4] if len(user) > 4 else None  # team (user[3] 인덱스는 password)
            st.session_state['team_color'] = user[5] if len(user) > 5 else color_palette[0]  # team_color
            st.session_state['register'] = False  # 회원가입 상태 초기화

            if student_id == "admin_id":  # 예: 관리자의 학번을 특정 값으로 설정
                st.session_state['is_admin'] = True

            st.success("로그인 성공")
            st.experimental_rerun()
        else:
            st.error("학번이나 비밀번호가 올바르지 않습니다.")
    if st.button("회원가입"):
        st.session_state['register'] = True
        st.experimental_rerun()

# 회원가입 페이지
def register_page():
    st.title("회원가입 페이지")
    new_student_id = st.text_input("학번 (8자리 숫자)", key="register_student_id")
    new_name = st.text_input("이름 (한글)", key="register_name")
    new_password = st.text_input("비밀번호", type="password", key="register_password")
    new_team = st.selectbox("팀을 선택하세요", ["팀 A", "팀 B", "팀 C"], key="register_team")
    
    st.write("팀 컬러를 선택하세요")
    color_selected = st.radio("", color_palette, format_func=lambda color: f'<div style="background-color:{color}; width: 20px; height: 20px; border-radius: 50%;"></div>', key="register_team_color")

    if st.button("회원가입", key="register_button"):
        if len(new_student_id) == 8 and new_student_id.isdigit() and all('\uAC00' <= char <= '\uD7A3' for char in new_name):
            add_user(new_student_id, new_name, new_password, new_team, color_selected)
            st.success("회원가입이 완료되었습니다.")
            st.session_state['register'] = False  # 회원가입 완료 후 로그인 페이지로 이동
            st.experimental_rerun()
        else:
            st.error("유효한 학번(8자리 숫자)과 이름(한글)을 입력해주세요.")
    if st.button("로그인 페이지로 돌아가기", key="back_to_login_button"):
        st.session_state['register'] = False
        st.experimental_rerun()

# 메인 페이지
def main_page():
    st.title("실험실 예약 시스템")
    st.write(f"환영합니다, {st.session_state['user_name']}님 (학번: {st.session_state['student_id']})")

    # 사이드바 메뉴
    with st.sidebar:
        selected = option_menu(
            "메뉴",
            ["예약", "마이 페이지", "관리자 페이지" if st.session_state['is_admin'] else None],
            icons=["calendar-check", "person", "gear"],
            menu_icon="menu-button-wide",
            default_index=0,
        )

    if selected == "예약":
        # 날짜 선택
        st.subheader("예약 날짜 선택")
        selected_date = st.date_input("예약 날짜를 선택하세요", value=date.today(), min_value=date.today())
        st.session_state['selected_date'] = selected_date

        # 시간 선택 타일
        st.subheader("예약 시간 선택")
        times = [time(hour, minute) for hour in range(24) for minute in (0, 30)]
        
        now = datetime.now()
        available_times = [t for t in times if (selected_date > date.today()) or (selected_date == date.today() and datetime.combine(date.today(), t) > now)]
        
        selected_times = st.multiselect("예약할 시간을 선택하세요", available_times, format_func=lambda t: t.strftime("%H:%M"))

        # 예약 시간 검증 및 설정
        if selected_times:
            start_time = min(selected_times)
            end_time = max(selected_times)

            if start_time >= end_time:
                st.error("종료 시간은 시작 시간 이후여야 합니다.")
            elif (datetime.combine(date.today(), end_time) - datetime.combine(date.today(), start_time)).seconds % 1800 != 0:
                st.error("예약 시간은 30분 단위로 설정되어야 합니다.")
            else:
                # 예약 버튼
                if st.button("예약하기", key="reservation_confirm_button"):
                    insert_reservation(st.session_state['student_id'], start_time.strftime('%H:%M:%S'), end_time.strftime('%H:%M:%S'), selected_date)
                    st.success("예약이 완료되었습니다.")

        # 예약 목록 표시
        st.subheader("예약 목록")
        reservations = get_reservations()
        st.dataframe(reservations)

# 예약 현황 간트 차트
        st.subheader("예약 현황")
        gantt_data = []
        for _, row in reservations.iterrows():
            reservation_date = datetime.strptime(row['reservation_date'], '%Y-%m-%d').date()
            start_time = datetime.strptime(row['start_time'], '%H:%M:%S').time()
            end_time = datetime.strptime(row['end_time'], '%H:%M:%S').time()
            gantt_data.append(dict(
                Task=row['team'],
                Start=datetime.combine(reservation_date, start_time),
                Finish=datetime.combine(reservation_date, end_time),
                Resource=row['team'],
                Color=row['team_color']
            ))

        fig = go.Figure()

        for task in gantt_data:
            fig.add_trace(go.Bar(
                x=[task['Start'], task['Finish']],
                y=[task['Task'], task['Task']],
                orientation='h',
                marker=dict(color=task['Color']),
                showlegend=False,
                hoverinfo='x+y'
            ))

        fig.update_layout(
            barmode='stack',
            title="팀별 예약 현황",
            xaxis_title="시간",
            yaxis_title="팀",
            height=600,
        )

        st.plotly_chart(fig)     

    elif selected == "마이 페이지":
        my_page()
    elif selected == "관리자 페이지" and st.session_state['is_admin']:
        admin_page()

# 마이 페이지
def my_page():
    st.subheader("마이 페이지")
    st.write(f"환영합니다, {st.session_state['user_name']}님 (학번: {st.session_state['student_id']}, 팀: {st.session_state['team']})")

    # 개인정보 수정
    if st.button("개인정보 수정"):
        st.session_state['edit_profile'] = True

    if st.session_state.get('edit_profile', False):
        new_name = st.text_input("이름 (한글)", value=st.session_state['user_name'])
        new_student_id = st.text_input("학번 (8자리 숫자)", value=st.session_state['student_id'])
        new_team = st.selectbox("팀을 선택하세요", ["팀 A", "팀 B", "팀 C"], index=0)
        
        st.write("팀 컬러를 선택하세요")
        if st.session_state['team_color'] is None:
            st.session_state['team_color'] = color_palette[0]
        new_team_color = st.radio("", color_palette, index=color_palette.index(st.session_state['team_color']), format_func=lambda color: f'<div style="background-color:{color}; width: 20px; height: 20px; border-radius: 50%;"></div>')

        if st.button("저장", key="save_profile"):
            update_user(st.session_state['student_id'], new_name, new_team, new_student_id, new_team_color)
            st.session_state['user_name'] = new_name
            st.session_state['team'] = new_team
            st.session_state['student_id'] = new_student_id
            st.session_state['team_color'] = new_team_color
            st.success("개인정보가 수정되었습니다.")
            st.session_state['edit_profile'] = False
            st.experimental_rerun()

    # 이번 주 예약된 시간 계산 및 표시
    reserved_time = get_reserved_time(st.session_state['student_id'])
    remaining_time = 24 - reserved_time

    st.write(f"이번 주 예약 가능 시간: {remaining_time} 시간")
    st.write(f"이번 주 예약한 시간: {reserved_time} 시간")

    # 가로 바 그래프
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=["시간"],
        x=[remaining_time],
        name="잔여 시간",
        orientation='h',
        marker=dict(color='gray')
    ))
    fig.add_trace(go.Bar(
        y=["시간"],
        x=[reserved_time],
        name="예약한 시간",
        orientation='h',
        marker=dict(color='blue')  # 원하는 색으로 변경
    ))

    fig.update_layout(
        barmode='stack',
        title="이번 주 예약 가능 시간",
        xaxis=dict(showgrid=False, tickvals=[0, 4, 8, 12, 16, 20, 24], ticktext=["0", "4", "8", "12", "16", "20", "24"]),
        yaxis=dict(showgrid=False),
        showlegend=False,
        height=200,
    )

    st.plotly_chart(fig)

# 관리자 페이지
def admin_page():
    st.subheader("관리자 페이지")
    st.write("여기에서 관리자 기능을 구현할 수 있습니다.")

# 페이지 라우팅
if st.session_state['logged_in']:
    main_page()
elif st.session_state['register']:
    register_page()
else:
    login_page()
