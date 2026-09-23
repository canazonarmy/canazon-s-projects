
import pygame
import cv2
import mediapipe as mp
import random
import threading
import time
import numpy as np
import os

# -------------------- INITIALIZATION --------------------

pygame.init()

WIDTH, HEIGHT = 800, 600

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Body-Controlled Ball Collecting Game")

clock = pygame.time.Clock()

font = pygame.font.SysFont(None, 32)
big_font = pygame.font.SysFont(None, 54)
small_font = pygame.font.SysFont(None, 24)

WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 100, 255)
BLACK = (0, 0, 0)
GREEN = (0, 180, 0)
ORANGE = (255, 150, 0)
GRAY = (180, 180, 180)

# -------------------- GAME VARIABLES --------------------

player_pos = [WIDTH // 2, HEIGHT - 100]

ball_pos = [
    random.randint(50, WIDTH - 50),
    -50
]

ball_speed = 3

score = 0
time_limit = 60
start_time = time.time()

SMOOTHING_FACTOR = 0.1

# -------------------- HIGH SCORE --------------------

HIGH_SCORE_FILE = "highscore.txt"

try:
    if os.path.exists(HIGH_SCORE_FILE):
        with open(HIGH_SCORE_FILE, "r") as file:
            high_score = int(file.read().strip())
    else:
        high_score = 0
except:
    high_score = 0

def save_high_score():
    global high_score

    if score > high_score:
        high_score = score

        try:
            with open(HIGH_SCORE_FILE, "w") as file:
                file.write(str(high_score))
        except:
            pass

# -------------------- MEDIAPIPE --------------------

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    smooth_landmarks=True,
    enable_segmentation=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# -------------------- CAMERA --------------------

cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# -------------------- THREAD SHARED VARIABLES --------------------

frame_lock = threading.Lock()

current_frame = None

hand_x = WIDTH // 2
hand_y = HEIGHT // 2

pose_landmarks = None

stop_event = threading.Event()

# Speed variables
previous_hand_x = None
previous_hand_y = None
previous_time = None

player_speed = 0.0
smooth_speed = 0.0

# Posture variables
posture_score = 100.0

# -------------------- VIDEO THREAD --------------------

def video_capture_thread():
    global current_frame
    global hand_x, hand_y
    global pose_landmarks
    global previous_hand_x, previous_hand_y
    global previous_time
    global player_speed, smooth_speed
    global posture_score

    while not stop_event.is_set():

        ret, frame = cap.read()

        if not ret:
            time.sleep(0.01)
            continue

        frame = cv2.flip(frame, 1)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = pose.process(rgb_frame)

        # Draw skeleton
        if results.pose_landmarks:

            mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(
                    color=(0, 255, 0),
                    thickness=2,
                    circle_radius=3
                ),
                mp_drawing.DrawingSpec(
                    color=(255, 0, 0),
                    thickness=2,
                    circle_radius=2
                )
            )

            landmarks = results.pose_landmarks.landmark

            # RIGHT WRIST
            right_wrist = landmarks[
                mp_pose.PoseLandmark.RIGHT_WRIST
            ]

            target_x = int(right_wrist.x * WIDTH)
            target_y = int(right_wrist.y * HEIGHT)

            hand_x = target_x
            hand_y = target_y

            # ---------------- SPEED CALCULATION ----------------

            current_time = time.time()

            if previous_hand_x is not None and previous_time is not None:

                dt = current_time - previous_time

                if dt > 0:

                    dx = right_wrist.x - previous_hand_x
                    dy = right_wrist.y - previous_hand_y

                    distance = np.sqrt(
                        dx * dx + dy * dy
                    )

                    player_speed = distance / dt

                    smooth_speed = (
                        smooth_speed * 0.8
                        + player_speed * 0.2
                    )

            previous_hand_x = right_wrist.x
            previous_hand_y = right_wrist.y
            previous_time = current_time

            # ---------------- POSTURE CALCULATION ----------------

            left_shoulder = landmarks[
                mp_pose.PoseLandmark.LEFT_SHOULDER
            ]

            right_shoulder = landmarks[
                mp_pose.PoseLandmark.RIGHT_SHOULDER
            ]

            left_hip = landmarks[
                mp_pose.PoseLandmark.LEFT_HIP
            ]

            right_hip = landmarks[
                mp_pose.PoseLandmark.RIGHT_HIP
            ]

            # Shoulder alignment
            shoulder_difference = abs(
                left_shoulder.y - right_shoulder.y
            )

            shoulder_score = max(
                0,
                100 - shoulder_difference * 800
            )

            # Hip alignment
            hip_difference = abs(
                left_hip.y - right_hip.y
            )

            hip_score = max(
                0,
                100 - hip_difference * 800
            )

            # Torso verticality
            shoulder_center_x = (
                left_shoulder.x + right_shoulder.x
            ) / 2

            shoulder_center_y = (
                left_shoulder.y + right_shoulder.y
            ) / 2

            hip_center_x = (
                left_hip.x + right_hip.x
            ) / 2

            hip_center_y = (
                left_hip.y + right_hip.y
            ) / 2

            torso_dx = abs(
                shoulder_center_x - hip_center_x
            )

            torso_score = max(
                0,
                100 - torso_dx * 600
            )

            posture_score = (
                shoulder_score * 0.35
                + hip_score * 0.25
                + torso_score * 0.40
            )

            # Save landmark data
            pose_landmarks = results.pose_landmarks

        with frame_lock:
            current_frame = frame.copy()

        time.sleep(0.005)

# -------------------- START THREAD --------------------

thread = threading.Thread(
    target=video_capture_thread,
    daemon=True
)

thread.start()

# -------------------- GAME FUNCTIONS --------------------

def draw_player(player_pos):

    pygame.draw.rect(
        screen,
        BLUE,
        (
            int(player_pos[0]),
            int(player_pos[1]),
            100,
            50
        ),
        border_radius=10
    )

def draw_ball(ball_pos):

    pygame.draw.circle(
        screen,
        RED,
        (
            int(ball_pos[0]),
            int(ball_pos[1])
        ),
        20
    )

def check_collision(player_pos, ball_pos):

    px, py = player_pos
    bx, by = ball_pos

    return (
        px < bx < px + 100
        and
        py < by < py + 50
    )

def smooth_move(current_pos, target_pos, smoothing_factor):

    return (
        current_pos
        +
        (target_pos - current_pos)
        * smoothing_factor
    )

# -------------------- RATING --------------------

def calculate_speed_score(speed):

    # Normal movement speed gives a high score.
    # Very high values are capped.

    speed_score = speed * 180

    speed_score = max(
        0,
        min(100, speed_score)
    )

    return speed_score

def calculate_rating():

    speed_rating = calculate_speed_score(
        smooth_speed
    )

    overall = (
        speed_rating * 0.60
        +
        posture_score * 0.40
    )

    return int(
        max(
            0,
            min(100, overall)
        )
    )

def rating_color(rating):

    if rating >= 80:
        return GREEN

    if rating >= 60:
        return ORANGE

    return RED

# -------------------- CAMERA DISPLAY --------------------

def draw_cam_feed():

    with frame_lock:

        if current_frame is not None:

            cam_frame = cv2.cvtColor(
                current_frame,
                cv2.COLOR_BGR2RGB
            )

            cam_frame = cv2.resize(
                cam_frame,
                (320, 240)
            )

            cam_surface = pygame.surfarray.make_surface(
                np.rot90(cam_frame)
            )

            screen.blit(
                cam_surface,
                (
                    WIDTH - 330,
                    10
                )
            )

            pygame.draw.rect(
                screen,
                BLACK,
                (
                    WIDTH - 330,
                    10,
                    320,
                    240
                ),
                2
            )

def draw_stats():

    speed_rating = int(
        calculate_speed_score(
            smooth_speed
        )
    )

    rating = calculate_rating()

    # Panel
    panel_x = 10
    panel_y = 50
    panel_w = 250
    panel_h = 160

    pygame.draw.rect(
        screen,
        WHITE,
        (
            panel_x,
            panel_y,
            panel_w,
            panel_h
        ),
        border_radius=10
    )

    pygame.draw.rect(
        screen,
        BLACK,
        (
            panel_x,
            panel_y,
            panel_w,
            panel_h
        ),
        2,
        border_radius=10
    )

    speed_text = font.render(
        f"Speed: {speed_rating}/100",
        True,
        BLACK
    )

    posture_text = font.render(
        f"Posture: {int(posture_score)}/100",
        True,
        BLACK
    )

    rating_text = font.render(
        f"Rating: {rating}/100",
        True,
        rating_color(rating)
    )

    high_score_text = font.render(
        f"High Score: {high_score}",
        True,
        BLACK
    )

    screen.blit(
        speed_text,
        (20, 60)
    )

    screen.blit(
        posture_text,
        (20, 95)
    )

    screen.blit(
        rating_text,
        (20, 130)
    )

    screen.blit(
        high_score_text,
        (20, 165)
    )

def draw_score():

    score_text = font.render(
        f"Score: {score}",
        True,
        BLACK
    )

    screen.blit(
        score_text,
        (
            WIDTH // 2 - 55,
            10
        )
    )

def draw_timer(time_left):

    timer_text = font.render(
        f"Time: {time_left}",
        True,
        BLACK
    )

    screen.blit(
        timer_text,
        (
            WIDTH - 120,
            260
        )
    )

# -------------------- GAME LOOP --------------------

running = True

while running:

    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            running = False

        if (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_ESCAPE
        ):

            running = False

        if event.type == pygame.VIDEORESIZE:

            WIDTH = max(640, event.w)
            HEIGHT = max(480, event.h)

            screen = pygame.display.set_mode(
                (WIDTH, HEIGHT),
                pygame.RESIZABLE
            )

    # ---------------- PLAYER MOVEMENT ----------------

    player_pos[0] = smooth_move(
        player_pos[0],
        hand_x - 50,
        SMOOTHING_FACTOR
    )

    player_pos[1] = smooth_move(
        player_pos[1],
        hand_y - 25,
        SMOOTHING_FACTOR
    )

    player_pos[0] = max(
        0,
        min(
            player_pos[0],
            WIDTH - 100
        )
    )

    player_pos[1] = max(
        0,
        min(
            player_pos[1],
            HEIGHT - 50
        )
    )

    # ---------------- BALL ----------------

    ball_pos[1] += ball_speed

    if ball_pos[1] > HEIGHT:

        ball_pos = [
            random.randint(
                50,
                max(51, WIDTH - 50)
            ),
            -50
        ]

    if check_collision(
        player_pos,
        ball_pos
    ):

        score += 1

        ball_pos = [
            random.randint(
                50,
                max(51, WIDTH - 50)
            ),
            -50
        ]

        save_high_score()

    # ---------------- TIMER ----------------

    elapsed_time = (
        time.time()
        - start_time
    )

    time_left = max(
        0,
        int(
            time_limit
            - elapsed_time
        )
    )

    if time_left <= 0:

        running = False

    # ---------------- DRAW ----------------

    screen.fill(WHITE)

    draw_player(player_pos)

    draw_ball(ball_pos)

    draw_score()

    draw_timer(time_left)

    draw_stats()

    draw_cam_feed()

    pygame.display.flip()

    clock.tick(60)

# -------------------- END GAME --------------------

save_high_score()

final_rating = calculate_rating()

screen.fill(WHITE)

title = big_font.render(
    "GAME OVER",
    True,
    BLACK
)

final_score = font.render(
    f"Your Score: {score}",
    True,
    BLACK
)

best_score = font.render(
    f"High Score: {high_score}",
    True,
    BLACK
)

final_speed = font.render(
    f"Speed Rating: {int(calculate_speed_score(smooth_speed))}/100",
    True,
    BLACK
)

final_posture = font.render(
    f"Posture Rating: {int(posture_score)}/100",
    True,
    BLACK
)

final_rating_text = big_font.render(
    f"FINAL RATING: {final_rating}/100",
    True,
    rating_color(final_rating)
)

screen.blit(
    title,
    (
        WIDTH // 2 - title.get_width() // 2,
        120
    )
)

screen.blit(
    final_score,
    (
        WIDTH // 2 - final_score.get_width() // 2,
        200
    )
)

screen.blit(
    best_score,
    (
        WIDTH // 2 - best_score.get_width() // 2,
        240
    )
)

screen.blit(
    final_speed,
    (
        WIDTH // 2 - final_speed.get_width() // 2,
        280
    )
)

screen.blit(
    final_posture,
    (
        WIDTH // 2 - final_posture.get_width() // 2,
        320
    )
)

screen.blit(
    final_rating_text,
    (
        WIDTH // 2 - final_rating_text.get_width() // 2,
        380
    )
)

pygame.display.flip()

pygame.time.wait(4000)

# -------------------- CLEANUP --------------------

stop_event.set()

cap.release()

pose.close()

pygame.quit()

cv2.destroyAllWindows()