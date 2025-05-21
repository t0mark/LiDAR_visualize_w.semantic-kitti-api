# semantic-kitti-api 개량
### 내용
- 개인 프로젝트의 필요에 맞춰 내용을 수정
  - label: [car, other-vehicle, road, sidewalk, unlabeled] 확인
  - 데이터 형식이 [x, y, z, intensity, label]인 경우 확인
- semantic segmentation 된 결과를 확인하기 위한 도구
- 학습 결과에 맞춰 색상 표현 변경
  - 라벨이 몇 개든 어떤 모델이든 mapping 가능
  - 설정 파일의 label_map 설정

### 참조
- [semantic-kitti-api](https://github.com/PRBonn/semantic-kitti-api)

### 환경
- Unbuntu 20.04 LTS
- CUDA : 11.2
- NVIDIA 드라이버 : 470.256

### build
``` bash
pip3 install matplotlib vispy torch numpy PyYAML "imgui[glfw]" glfw PyOpenGL
sudo apt install build-essential libgl1-mesa-dev libxkbcommon-x11-0
pip3 install PyQt5-Qt5==5.15.2
pip3 install PyQt5==5.15.4
```

### 파일 구조
- config 파일 및 실행 옵션에 따라 파일 구성
- config/ 파일 참조
```
/lidar_data_path
    ├── 00/
    │   ├── velodyne/
    │   │   ├ 000000.bin
    │   │   └ 000001.bin
    │   └── labels/
    │        ├ 000000.label
    │        └ 000001.label
    ├── 01/
    │   ├── ouster/
    │   │   ├ 000000.bin
    │   │   └ 000001.bin
    ├── 02/
```

### 실행
``` bash
# .bin: [x, y, z, intensity], .label: [semantic label, instance label]
./visualize.py \
  -d {lidar_data_path/sequence 번호 경로} \
  -c {config 경로}

# 오픈 데이터셋 label 사용 시 config 파일 간략화 (중복 제거)
./visualize.py \
  -d {lidar_data_path/sequence 번호 경로} \
  -c {config 경로} \
  --open-data {오픈 데이터셋 이름}

# ./bin [x, y, z, intensity, label], .lael: 사용 X
./visualize.py \
  -d {lidar_data_path/sequence 번호 경로} \
  -c {config 경로} \
  --predictions

# 프로젝트에 맞춘 라벨로 보기 [car, other-vehicle, road, sidewalk, unlabeled]
./visualize.py \
  -d {lidar_data_path/sequence 번호 경로} \
  -c {config 경로} \
  --mapping
```

- 사용법
  - n: 다음 스캔
  - b: 이전 스캔
  - esc 또는 q: 종료

### 결과
- 파랑색 : car
- 초록색 : other-vehicle
- 빨강색 : road
- 노랑색 : side-walk
- 흰색 : unlabeled
  ![image](./docs/result.png)
