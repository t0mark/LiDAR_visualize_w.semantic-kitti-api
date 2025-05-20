#!/usr/bin/env python3
import numpy as np
import yaml


class LaserScan:

    # pointcloud 파일 확장자
    EXTENSIONS_SCAN = ['.bin']

    def __init__(self, project=False, H=64, W=1024, fov_up=3.0, fov_down=-25.0):
        self.project = project
        self.proj_H = H
        self.proj_W = W
        self.proj_fov_up = fov_up
        self.proj_fov_down = fov_down
        self.combined = False
        self.reset()

    def set_combined(self, combined):
        self.combined = combined

    def set_mapping(self, mapping):
        self.mapping = mapping


    # 새로운 LiDAR scan을 처리할 준비
    def reset(self):

        # [x, y, z, intensity] -> position과 intensity를 각각 저장
        ## [x, y, z]: [m, 3]
        ## [inensity]: [m, 1]
        ### m: variable size, point의 개수
        self.points = np.zeros((0, 3), dtype=np.float32)
        self.intensity = np.zeros((0, 1), dtype=np.float32)

        # 3D -> 2D 전환 (이미지가 여러 정보를 포함)
        ## 정보1: 각 point의 거리
        self.proj_range = np.full((self.proj_H, self.proj_W), -1, dtype=np.float32)
        ## 정보2: 3D 좌표 공간 (x, y, z)
        self.proj_xyz = np.full((self.proj_H, self.proj_W, 3), -1, dtype=np.float32)
        ## 정보3: 반사 강도 (intensity)
        self.proj_intensity = np.full((self.proj_H, self.proj_W), -1, dtype=np.float32)
        ## 정보4: 원본 3D point의 index
        self.proj_idx = np.full((self.proj_H, self.proj_W), -1, dtype=np.int32)
        ## 정보5: 2D 이미지 실제 포인트 투영 여부 (1 또는 0)
        self.proj_mask = np.zeros((self.proj_H, self.proj_W), dtype=np.int32)

        # 3D -> 2D 계산 중 사용되는 변수
        ## point의 2D 좌표
        self.proj_x = np.zeros((0, 1), dtype=np.float32)
        self.proj_y = np.zeros((0, 1), dtype=np.float32)
        ## point의 거리 정보
        self.unproj_range = np.zeros((0, 1), dtype=np.float32)

    def size(self):
        return self.points.shape[0]

    def __len__(self):
        return self.size()


    # LiDAR scan 열기
    def open_scan(self, filename):

        # 1. 기존 데이터 초기화
        self.reset()

        # 2. 파일 유효성 검사
        ## 파일명 검증
        if not isinstance(filename, str):
            raise TypeError(f"파일명이 오류, 현재 type: {str(type(filename))}")
        ## 파일 확장자 검증
        if not any(filename.endswith(ext) for ext in self.EXTENSIONS_SCAN):
            raise RuntimeError("파일 확장자 오류")

        # 3. pointcloud 불러오기
        scan = np.fromfile(filename, dtype=np.float32)
        if self.combined:
            # combined 모드 처리: [x, y, z, intensity, label] 형식
            scan = scan.reshape((-1, 5))
            points = scan[:, 0:3]
            intensity = scan[:, 3]
            labels = scan[:, 4].astype(np.uint32)
            self.set_points(points, intensity)
            if hasattr(self, "set_label"):
                self.set_label(labels)
        else:
            # 기존 방식: [x, y, z, intensity] 형식으로 파일을 해석
            scan = scan.reshape((-1, 4))
            points = scan[:, 0:3]
            intensity = scan[:, 3]
            self.set_points(points, intensity)

    # pointcloud 설정
    def set_points(self, points, intensity=None):

        # 1. 기존 데이터 초기화
        self.reset()

        # 2. 입력 데이터 유효성 검사
        ## points type 검증
        if not isinstance(points, np.ndarray):
            raise TypeError("Scan type 오류")
        # intensity type 검증
        if intensity is not None and not isinstance(intensity, np.ndarray):
            raise TypeError("intensity type 오류")

        # 3. 멤버 변수 설정 (points, intensity)
        self.points = points
        if intensity is not None:
            self.intensity = intensity
        else:
            self.intensity = np.zeros((points.shape[0]), dtype=np.float32)

        # 4. 2D 투영 실행
        if self.project:
            self.do_range_projection()

    # pointcloud 2D 투영 변환
    def do_range_projection(self):
        
        # 1. LiDAR 센서 파라미터 설정
        fov_up = self.proj_fov_up / 180.0 * np.pi
        fov_down = self.proj_fov_down / 180.0 * np.pi
        fov = abs(fov_down) + abs(fov_up)

        # 2. 기본 계산값 준비
        ## 원점 - 각 포인트 거리
        depth = np.linalg.norm(self.points, 2, axis=1)

        # 각 포인트 성분 추출 (x, y, z)
        scan_x = self.points[:, 0]
        scan_y = self.points[:, 1]
        scan_z = self.points[:, 2]

        # 3. 구면 좌표계 각도 계산 (수평각, 수직각)
        yaw = -np.arctan2(scan_y, scan_x)
        pitch = np.arcsin(scan_z / (depth + 1e-8))

        # 4. 3D 각도 -> 2D 이미지 변환 준비
        ## 정규화 변환 (-pi, pi) -> (0, 1)
        proj_x = 0.5 * (yaw / np.pi + 1.0)
        proj_y = 1.0 - (pitch + abs(fov_down)) / fov

        ## 정규화 좌표 -> 실제 이미지 크기에 맞게 스케일링
        proj_x *= self.proj_W
        proj_y *= self.proj_H

        # 5. 픽셀 index 처리 (원본 순서대로 처리)
        ## 좌표 저장
        proj_x = np.floor(proj_x)
        proj_x = np.minimum(self.proj_W - 1, proj_x)
        proj_x = np.maximum(0, proj_x).astype(np.int32)
        self.proj_x = np.copy(proj_x)

        proj_y = np.floor(proj_y)
        proj_y = np.minimum(self.proj_H - 1, proj_y)
        proj_y = np.maximum(0, proj_y).astype(np.int32)
        self.proj_y = np.copy(proj_y)

        ## 거리 저장
        self.unproj_range = np.copy(depth)

        # 6. 거리 기준 정렬 (내림차순)
        indices = np.arange(depth.shape[0])
        order = np.argsort(depth)[::-1]
        depth = depth[order]
        indices = indices[order]
        points = self.points[order]
        intensity = self.intensity[order]
        proj_y = proj_y[order]
        proj_x = proj_x[order]

        # 7. 3D -> 2D 이미지 할당
        self.proj_range[proj_y, proj_x] = depth
        self.proj_xyz[proj_y, proj_x] = points
        self.proj_intensity[proj_y, proj_x] = intensity
        self.proj_idx[proj_y, proj_x] = indices
        self.proj_mask = (self.proj_idx > 0).astype(np.float32)


# semantic segmentation label 처리 기능 추가
class SemLaserScan(LaserScan):

    # label 파일 확장자
    EXTENSIONS_LABEL = ['.label']

    def __init__(self, sem_color_dict=None, project=False, H=64, W=1024, fov_up=3.0, fov_down=-25.0):
        super(SemLaserScan, self).__init__(project, H, W, fov_up, fov_down)
        self.combined = False
        self.mapping = False
        self.reset()

        # 최대 클래스 ID 찾기
        max_sem_key = 0
        for key, data in sem_color_dict.items():
            if key + 1 > max_sem_key:
                max_sem_key = key + 1
        
        # semantic color look-up 테이블 생성
        self.sem_color_lut = np.zeros((max_sem_key + 100, 3), dtype=np.float32)
        ## 각 클래스의 색상 정보 저장 (0 ~ 255 -> 0 ~ 1)
        for key, value in sem_color_dict.items():
            self.sem_color_lut[key] = np.array(value, np.float32) / 255.0

        # instance label color look-up 테이블 생성
        max_inst_id = 100000
        self.inst_color_lut = np.random.uniform(low=0.0,
                                                high=1.0,
                                                size=(max_inst_id, 3))
        ## instance 미분류 -> 회색
        self.inst_color_lut[0] = np.full((3), 0.1)
    
    def set_label_map(self, label_map):
        self.label_map = label_map

    # 새로운 LiDAR scan을 처리할 준비
    def reset(self):

        # 부모 클래스 메서드 호출
        ## 2D 이미지 정보, 3D -> 2D 변환 중 계산에 사용되는 변수
        super(SemLaserScan, self).reset()

        # semantic labels
        ## label: [m, 1]
        ## color: [m, 3] (B, G, R)
        self.sem_label = np.zeros((0, 1), dtype=np.uint32)
        self.sem_label_color = np.zeros((0, 3), dtype=np.float32)

        # instance labels
        self.inst_label = np.zeros((0, 1), dtype=np.uint32)
        self.inst_label_color = np.zeros((0, 3), dtype=np.float32)

        # 2D 이미지 정보
        ## 정보6: semantic labels
        self.proj_sem_label = np.zeros((self.proj_H, self.proj_W), dtype=np.int32)
        self.proj_sem_color = np.zeros((self.proj_H, self.proj_W, 3), dtype=float)

        ## 정보6: semantic labels
        self.proj_inst_label = np.zeros((self.proj_H, self.proj_W), dtype=np.int32)
        self.proj_inst_color = np.zeros((self.proj_H, self.proj_W, 3), dtype=float)


    # Label 파일 열기
    def open_label(self, filename):
        
        # 1. 입력 데이터 유효성 검사
        ## 파일명 검증
        if not isinstance(filename, str):
            raise TypeError(f"파일명이 오류, 현재 type: {str(type(filename))}")
        ## 파일 확장자 검증
        if not any(filename.endswith(ext) for ext in self.EXTENSIONS_LABEL):
            raise RuntimeError("Filename extension is not valid label file.")

        # 2. label 불러오기
        ## combined 모드는 open_scan에서 처리 (파일 두 번 읽기 방지)
        label = np.fromfile(filename, dtype=np.uint32)
        label = label.reshape((-1))
        self.set_label(label)

    # label 설정
    def set_label(self, label):
        
        # 1. 입력 데이터 유효성 검사
        ## label type 검증
        if not isinstance(label, np.ndarray):
            raise TypeError("label type 오류")
        
        # 2. point 수와 label 수 비교
        if label.shape[0] == self.points.shape[0]:
            # 3. 32bit label 분리
            ## label (32bit) = instance label (16bit) + semantic label (16bit)
            self.sem_label = label & 0xFFFF
            self.inst_label = label >> 16
        else:
            print("Points 개수: ", self.points.shape)
            print("Label 개수: ", label.shape)
            raise ValueError("Scan과 Label의 개수가 다름")
        
        # 4. 분리된 label과 원본 label 비교
        assert((self.sem_label + (self.inst_label << 16) == label).all())

        if self.mapping:
            # mapping 모드 처리: 원본 label -> [unlabeld, road, sidewalk, car, other-vehicle]
            mapped_label = np.copy(self.sem_label)
            for key, val in self.label_map.items():
                mapped_label[self.sem_label == key] = val
            self.sem_label = mapped_label

        # 5. 2D 투영 실행
        if self.project:
            self.do_label_projection()

    # 색상 할당
    def colorize(self):
        # semantic 색상 할당
        self.sem_label_color = self.sem_color_lut[self.sem_label]
        self.sem_label_color = self.sem_label_color.reshape((-1, 3))

        # instance 색상 할당
        self.inst_label_color = self.inst_color_lut[self.inst_label]
        self.inst_label_color = self.inst_label_color.reshape((-1, 3))

    # label 2D 투영 변환
    def do_label_projection(self):
        # 1. 유효한 픽셀만 선택
        mask = self.proj_idx >= 0

        # 2. 2D 이미지 정보
        ## 정보7: label
        ## semantic
        self.proj_sem_label[mask] = self.sem_label[self.proj_idx[mask]]
        self.proj_sem_color[mask] = self.sem_color_lut[self.sem_label[self.proj_idx[mask]]]

        ## instances
        self.proj_inst_label[mask] = self.inst_label[self.proj_idx[mask]]
        self.proj_inst_color[mask] = self.inst_color_lut[self.inst_label[self.proj_idx[mask]]]
