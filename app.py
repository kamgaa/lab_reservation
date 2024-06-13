import os
import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from datetime import datetime, date, timedelta, time
from streamlit_option_menu import option_menu
from config import PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR, BACKGROUND_COLOR, TEXT_COLOR, DATABASE_FILE
from database import add_user, check_user, init_db, get_reservations, get_users, insert_users_from_cache, insert_reservations_from_cache, insert_reservation
from streamlit_modal import Modal
import pytz
import requests
from github import Github

# GitHub 토큰을 Streamlit secrets에서 가져옵니다.
GITHUB_TOKEN = st.secrets["general"]["GITHUB_TOKEN"]
REPO_NAME = "kamgaa/lab_reservation"

@st.cache_resource
def download_db_from_github():
    url = f"https://github.com/{REPO_NAME}/raw/main/reservation.db"
    response = requests.get(url)
    if response.status_code == 200:
        with open("reservation.db", "wb") as f:
            f.write(response.content)
    else:
        st.error("Failed to download database file from GitHub.")
        st.stop()

@st.cache_resource
def load_from_db():
    users = get_users().to_dict(orient='records')
    reservations = get_reservations().to_dict(orient='records')
    return users, reservations

def upload_db_to_github():
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    with open("reservation.db", "rb") as file:
        content = file.read()
    try:
        contents = repo.get_contents("reservation.db", ref="main")
        repo.update_file(contents.path, "Update reservation database", content, contents.sha, branch="main")
    except:
        repo.create_file("reservation.db", "Create reservation database", content, branch="main")

def save_to_db():
    if 'users' in st.session_state:
        insert_users_from_cache(st.session_state['users'])
    if 'reservations' in st.session_state:
        insert_reservations_from_cache(st.session_state['reservations'])
    upload_db_to_github()

# 앱 시작 시 GitHub에서 데이터베이스 파일 다운로드 및 로드
if not os.path.exists("reservation.db"):
    try:
        download_db_from_github()
    except Exception as e:
        st.error(f"Failed to download database from GitHub: {e}")
        # 데이터베이스 파일이 없는 경우 새로 생성
        init_db()

# 데이터베이스 초기화 (기존 파일을 사용할 경우에도 테이블을 확인하고 초기화)
init_db()

if 'users' not in st.session_state or 'reservations' not in st.session_state:
    st.session_state['users'], st.session_state['reservations'] = load_from_db()

def save_reservation(student_id, start_time, end_time, reservation_date):
    st.session_state['reservations'].append({
        'student_id': student_id,
        'start_time': start_time,
        'end_time': end_time,
        'reservation_date': reservation_date
    })
    save_to_db()

def register_user(student_id, name, password, team, team_color):
    st.session_state['users'].append({
        'student_id': student_id,
        'name': name,
        'password': password,
        'team': team,
        'team_color': team_color
    })
    save_to_db()

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
            st.session_state['is_admin'] = (student_id == "24510047")  # 관리자인지 확인
            st.session_state['register'] = False  # 회원가입 상태 초기화

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
    new_team = st.selectbox("팀을 선택하세요", ["CAD_UAV", "Palletrone", "Ja!warm", "Crazyflie"], key="register_team")

    if st.button("회원가입", key="register_button"):
        if len(new_student_id) == 8 and new_student_id.isdigit() and all('\uAC00' <= char <= '\uD7A3' for char in new_name):
            team_color = TEAM_COLORS[new_team]
            register_user(new_student_id, new_name, new_password, new_team, team_color)
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
        st.subheader("예약 페이지")
        
        # 날짜 선택
        selected_date = st.date_input("예약 날짜를 선택하세요", value=date.today(), min_value=date.today())
        st.session_state['selected_date'] = selected_date

        # 현재 팀의 예약된 시간 계산
        reserved_time = get_reserved_time(st.session_state['team'])
        remaining_time = 24 - reserved_time

        if remaining_time <= 0:
            st.warning("이번 주에 더 이상 예약할 수 없습니다.")
            return

        st.write(f"이번 주 예약 가능 시간: {remaining_time} 시간")

        # 한국 시간대 설정
        kst = pytz.timezone('Asia/Seoul')
        
        # 시간대 리스트 생성
        time_slots = [time(hour, minute).strftime('%H:%M') for hour in range(24) for minute in (0, 30)]
        
        # 현재 시간으로부터 30분 후의 시간 설정
        next_half_hour = (datetime.now(kst) + timedelta(minutes=30)).replace(second=0, microsecond=0)
        if next_half_hour.minute < 30:
            next_half_hour = next_half_hour.replace(minute=30)
        else:
            next_half_hour = next_half_hour.replace(minute=0) + timedelta(hours=1)
        
        current_time_str = next_half_hour.strftime('%H:%M')

        # 시간 입력
        start_time = st.selectbox("시작 시간", options=time_slots, index=time_slots.index(current_time_str))
        end_time = st.selectbox("종료 시간", options=time_slots, index=time_slots.index((next_half_hour + timedelta(hours=1)).strftime('%H:%M')))

        start_time_dt = datetime.strptime(start_time, '%H:%M').time()
        end_time_dt = datetime.strptime(end_time, '%H:%M').time()

        if start_time_dt >= end_time_dt:
            st.error("종료 시간은 시작 시간 이후여야 합니다.")
        elif selected_date == date.today() and start_time_dt <= datetime.now().time():
            st.error("현재 시간 이후로 예약할 수 있습니다.")
        else:
            # 중복 예약 방지 로직 추가
            conn = get_connection()
            overlapping_reservations = pd.read_sql_query("""
                SELECT * FROM reservations 
                WHERE reservation_date = ? 
                AND (
                    (start_time < ? AND end_time > ?)
                )
            """, conn, params=(selected_date, end_time, start_time))
            conn.close()

            if overlapping_reservations.empty:
                # 예약 시간 검증 및 설정
                reservation_duration = (datetime.combine(date.today(), end_time_dt) - datetime.combine(date.today(), start_time_dt)).seconds / 3600
                if reservation_duration > remaining_time:
                    st.error(f"남은 예약 가능 시간을 초과했습니다. 남은 시간: {remaining_time} 시간")
                else:
                    # 예약 버튼
                    if st.button("예약하기", key="reservation_confirm_button"):
                        save_reservation(st.session_state['student_id'], start_time, end_time, selected_date)
                        st.success("예약이 완료되었습니다.")
                        st.experimental_rerun()
            else:
                st.error("다른 팀이 이미 해당 시간에 예약을 했습니다.")

        # 예약 목록 표시
        st.subheader("예약 목록")
        reservations = get_reservations()
        st.dataframe(reservations)

        # 예약 현황 바 차트
        st.subheader(f"{selected_date} 예약 현황")
        filtered_reservations = reservations[reservations['reservation_date'] == selected_date.strftime('%Y-%m-%d')]

        # 예약 데이터를 시간대별로 그룹화
        time_blocks = [(datetime.combine(selected_date, time(hour, 0)), datetime.combine(selected_date, time(hour + 1 if hour < 23 else 0, 0))) for hour in range(24)]
        reservation_summary = {block[0]: [] for block in time_blocks}

        for _, row in filtered_reservations.iterrows():
            reservation_start = datetime.combine(selected_date, datetime.strptime(row['start_time'], '%H:%M').time())
            reservation_end = datetime.combine(selected_date, datetime.strptime(row['end_time'], '%H:%M').time())
            for block_start, block_end in time_blocks:
                if reservation_start < block_end and reservation_end > block_start:
                    reservation_summary[block_start].append(row['team'])

        bar_data = []
        for block_start, teams in reservation_summary.items():
            team_counts = {team: teams.count(team) for team in set(teams)}
            for team, count in team_counts.items():
                bar_data.append({
                    'time': block_start.strftime('%H:%M'),
                    'team': team,
                    'count': 1  # 예약 건수는 1로 고정
                })

        bar_df = pd.DataFrame(bar_data)

        # 00시부터 24시까지 모든 시간을 보여주기 위해 빈 데이터도 포함
        empty_time_slots = [{'time': block_start.strftime('%H:%M'), 'team': '', 'count': 0} for block_start, _ in reservation_summary.items()]
        empty_df = pd.DataFrame(empty_time_slots)

        # 예약 데이터와 빈 데이터를 병합
        bar_df = pd.concat([bar_df, empty_df]).drop_duplicates(subset=['time', 'team']).reset_index(drop=True)

        if not bar_df.empty:
            fig = go.Figure()

            for team in bar_df['team'].unique():
                team_data = bar_df[bar_df['team'] == team]
                fig.add_trace(go.Bar(
                    x=team_data['time'],
                    y=team_data['count'],
                    name=team,
                    marker=dict(color=team_data['time'].apply(lambda x: TEAM_COLORS[team] if team in TEAM_COLORS else 'gray')),
                    showlegend=False if team == '' else True,  # 빈 팀은 레전드 표시 안 함
                ))

            fig.update_layout(
                title=f"{selected_date} 팀별 예약 현황",
                xaxis_title="예약 시간",
                yaxis_title=" ",
                yaxis=dict(tickvals=[1], ticktext=['1']),
                barmode='stack',
                xaxis=dict(type='category', categoryorder='category ascending')
            )

            st.plotly_chart(fig)
        else:
            st.write("선택한 날짜에 예약이 없습니다.")

    elif selected == "마이 페이지":
        my_page()
    elif selected == "관리자 페이지" and st.session_state['is_admin']:
        admin_page()

# 페이지 라우팅
if st.session_state['logged_in']:
    main_page()
elif st.session_state['register']:
    register_page()
else:
    login_page()
