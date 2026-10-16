# 3D Room Wallpaper

Logi 웹캠으로 얼굴을 추적해 눈의 위치(거리·각도)를 계산하고, 모니터를 "창문"처럼 취급하는
**off-axis 투영**으로 3D 방을 그려 윈도우 배경화면이 실제 공간처럼 보이게 합니다.

## 동작 원리
1. `tracker.py` – MediaPipe FaceMesh의 홍채 랜드마크(468/473)로 두 눈의 픽셀 위치를 얻습니다.
2. `head_pose.py` – 핀홀 모델: `거리 = 초점거리(px) × 실제 IPD(6.3cm) / 픽셀 IPD`. 웹캠 위치(모니터 위)를 보정해
   화면 중심 기준 눈 좌표 (x, y, z) cm 를 계산합니다.
3. `smoothing.py` – One-Euro 필터로 떨림 제거(정지 시 부드럽게, 움직임엔 빠르게).
4. `projection.py` – 눈 위치에 따라 비대칭 절두체를 만들어, 화면 평면이 항상 시야의 "창"이 되게 합니다.
5. `renderer.py` / `scene.py` – moderngl 로 방(격자 벽, 기둥, 화면 밖으로 튀어나오는 큐브)을 그립니다.
6. `wallpaper.py` – 창을 WorkerW 에 붙여 바탕화면 아이콘 뒤에 표시합니다.

## 실행
```
pip install -r requirements.txt
python -m room3d --windowed --mouse     # 웹캠 없이 마우스로 테스트
python -m room3d --windowed             # 웹캠 추적 테스트 (ESC 종료)
python -m room3d --wallpaper            # 배경화면으로 실행 (Windows)
```
옵션: `--screen-width-cm`(모니터 가로 실측), `--hfov`(웹캠 수평 화각), `--cam-offset-cm`(웹캠~모니터 상단 거리), `--camera`.

## 실감을 좌우하는 보정값
- **모니터 실제 가로 길이**: 틀리면 시차 크기가 어긋납니다. (27" 16:9 ≈ 59.8cm)
- **웹캠 화각**: C920/C922 ≈ 70° (16:9). Brio 는 설정에 따라 65/78/90°.
- **IPD**: 개인차가 있으면 `Config.ipd_cm` 조정 → 거리 추정이 바로 보정됩니다.

## 테스트
`pytest` – 투영/거리 추정/필터의 수학 검증 (GL·웹캠 불필요).

## 알려진 한계 / 다음 단계
- 실제 웹캠·Windows 환경에서는 아직 검증하지 못했습니다(개발 환경에 카메라/GPU 없음).
- 다중 모니터, 시작 프로그램 등록, 트레이 아이콘, 사용자 3D 모델(glTF)/텍스처 로딩은 미구현.
