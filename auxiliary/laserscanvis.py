#!/usr/bin/env python3
# This file is covered by the LICENSE file in the root of this project.

import vispy
from vispy.scene import visuals, SceneCanvas
import numpy as np
from matplotlib import pyplot as plt
from auxiliary.laserscan import LaserScan, SemLaserScan


# Scan 시각화 도구
class LaserScanVis:

    def __init__(self, 
                 scan, 
                 scan_names, 
                 label_names,
                 label=True,
                 combined=False,
                 mapping=False
                ):
        self.scan = scan
        self.scan_names = scan_names
        self.label_names = label_names
        self.semantics = label
        self.combined = combined
        self.mapping = mapping
        
        self.offset = 0
        self.total = len(self.scan_names)
        self.images = True
        self.instances = False

        self.reset()
        self.update_scan()

    # 시각화 인터페이스 초기화
    def reset(self):

        # 1. 기본 설정 초기화
        ## 키 입력 변수 (no, next, back, quit)
        self.action = "no"

        # 2. 3D pointcloud 시각화 창 설정
        ## 3D pointcloud 캔버스 생성
        self.canvas = SceneCanvas(keys='interactive', show=True)
        ## 키보드/그리기 이벤트 핸들러 연결
        self.canvas.events.key_press.connect(self.key_press)
        self.canvas.events.draw.connect(self.draw)
        ## grid layout 생성
        self.grid = self.canvas.central_widget.add_grid()

        # 2-1. 기본 거리 기반 pointcloud 시각화 (grid: (0,0))
        self.scan_view = vispy.scene.widgets.ViewBox(
                                                     border_color='white',
                                                     parent=self.canvas.scene
                                                    )
        self.grid.add_widget(self.scan_view, 0, 0)
        self.scan_vis = visuals.Markers(antialias=0)
        self.scan_view.camera = 'turntable'
        self.scan_view.add(self.scan_vis)
        visuals.XYZAxis(parent=self.scan_view.scene)

        # 2-2. semantic label 시각화 (grid: (0,1))
        if self.semantics:
            print("semantic label 사용 중...")
            self.sem_view = vispy.scene.widgets.ViewBox(
                                                        border_color='white', 
                                                        parent=self.canvas.scene
                                                       )
            self.grid.add_widget(self.sem_view, 0, 1)
            self.sem_vis = visuals.Markers(antialias=0)
            self.sem_view.camera = 'turntable'
            self.sem_view.add(self.sem_vis)
            visuals.XYZAxis(parent=self.sem_view.scene)
            self.sem_view.camera.link(self.scan_view.camera)

        # 2-3. instance label 시각화 (grid: (0,2))
        if self.instances:
            print("instance label 사용 중...")
            self.inst_view = vispy.scene.widgets.ViewBox(
                                                         border_color='white',
                                                         parent=self.canvas.scene
                                                        )
            self.grid.add_widget(self.inst_view, 0, 2)
            self.inst_vis = visuals.Markers(antialias=0)
            self.inst_view.camera = 'turntable'
            self.inst_view.add(self.inst_vis)
            visuals.XYZAxis(parent=self.inst_view.scene)
            self.inst_view.camera.link(self.scan_view.camera)

        # 3. 2D 이미지 시각화 창 설정
        if self.images:
            self.multiplier = 1
            self.canvas_W = self.scan.proj_W
            self.canvas_H = self.scan.proj_H
            if self.semantics:
                self.semantics += 1
            if self.instances:
                self.semantics += 1

            # 2D 이미지 캔버스 생성
            self.img_canvas = SceneCanvas(keys='interactive',
                                          show=True,
                                          size=(self.canvas_W, self.canvas_H * self.multiplier))
            ## grid layout 생성
            self.img_grid = self.img_canvas.central_widget.add_grid()
            ## 키보드/그리기 이벤트 핸들러 연결
            self.img_canvas.events.key_press.connect(self.key_press)
            self.img_canvas.events.draw.connect(self.draw)

            # 3-1. 기본 거리 기반 2D 이미지 시각화 (grid: (0,0))
            self.img_view = vispy.scene.widgets.ViewBox(
            border_color='white', parent=self.img_canvas.scene)
            self.img_grid.add_widget(self.img_view, 0, 0)
            self.img_vis = visuals.Image(cmap='viridis')
            self.img_view.add(self.img_vis)

            # 3-2. semantic label 시각화 (grid: (0,1))
            if self.semantics:
                self.sem_img_view = vispy.scene.widgets.ViewBox(
                                                                border_color='white',
                                                                parent=self.img_canvas.scene
                                                               )
            self.img_grid.add_widget(self.sem_img_view, 1, 0)
            self.sem_img_vis = visuals.Image(cmap='viridis')
            self.sem_img_view.add(self.sem_img_vis)

            # 3-3. instance label 시각화 (grid: (0,2))
            if self.instances:
                self.inst_img_view = vispy.scene.widgets.ViewBox(
                                                                 border_color='white',
                                                                 parent=self.img_canvas.scene
                                                                )
                self.img_grid.add_widget(self.inst_img_view, 2, 0)
                self.inst_img_vis = visuals.Image(cmap='viridis')
                self.inst_img_view.add(self.inst_img_vis)
                self.inst_view.camera.link(self.scan_view.camera)

    # matplotlib 컬러맵을 vispy에 맞게 변환
    def get_mpl_colormap(self, cmap_name):

        # 1. plt에 맞춰 컬러맵 가져오기
        cmap = plt.get_cmap(cmap_name)

        # 2. 색상 매핑 처리 객체 생성
        sm = plt.cm.ScalarMappable(cmap=cmap)

        # 3. 컬러맵에서 256개 색상 샘플 추출
        color_range = sm.to_rgba(np.linspace(0, 1, 256), bytes=True)[:, 2::-1]

        # 4. 최종 변환
        return color_range.reshape(256, 3).astype(np.float32) / 255.0

    # 현재 scan 로드 및 시각화
    def update_scan(self):
        
        # 1. 데이터 파일 열기
        ## 현재 scan 데이터 로드
        self.scan.open_scan(self.scan_names[self.offset])

        ## combined 모드 처리
        if self.semantics:
            if self.scan.combined:
                pass
            else:
                self.scan.open_label(self.label_names[self.offset])
                self.scan.colorize()

        # 2. 창 제목 업데이트
        title = "scan " + str(self.offset)
        self.canvas.title = title
        if self.images:
            self.img_canvas.title = title

        # 3-1. 3D pointcloud 시각화 (거리 기반 색상)
        ## 거리 값에 따라 색 강도 조정 (16등분)
        power = 16
        range_data = np.copy(self.scan.unproj_range)
        range_data = range_data**(1 / power)
        viridis_range = ((range_data - range_data.min()) /
                        (range_data.max() - range_data.min()) *
                        255).astype(np.uint8)
        viridis_map = self.get_mpl_colormap("viridis")
        viridis_colors = viridis_map[viridis_range]
        self.scan_vis.set_data(self.scan.points,
                               face_color=viridis_colors[..., ::-1],
                               edge_color=viridis_colors[..., ::-1],
                               size=1
                              )

        # 3-2. 3D pointcloud 시각화 (semantic label 기반 색상)
        if self.semantics:
            self.sem_vis.set_data(self.scan.points,
                                  face_color=self.scan.sem_label_color[..., ::-1],
                                  edge_color=self.scan.sem_label_color[..., ::-1],
                                  size=1
                                 )

        # 3-3. 3D pointcloud 시각화 (instance label 기반 색상)
        if self.instances:
            self.inst_vis.set_data(self.scan.points,
                                   face_color=self.scan.inst_label_color[..., ::-1],
                                   edge_color=self.scan.inst_label_color[..., ::-1],
                                   size=1
                                  )

        # 4-1. 2D 이미지 시각화 (거리 기반 색상)
        if self.images:
            data = np.copy(self.scan.proj_range)
            data[data > 0] = data[data > 0]**(1 / power)
            data[data < 0] = data[data > 0].min()
            data = ((data - data[data > 0].min()) / 
                    (data.max() - data[data > 0].min()))
            self.img_vis.set_data(data)
            self.img_vis.update()

            # 4-2. 2D 이미지 시각화 (semantic label 기반 색상)
            if self.semantics:
                self.sem_img_vis.set_data(self.scan.proj_sem_color[..., ::-1])
                self.sem_img_vis.update()

            # 4-2. 2D 이미지 시각화 (instance label 기반 색상)
            if self.instances:
                self.inst_img_vis.set_data(self.scan.proj_inst_color[..., ::-1])
                self.inst_img_vis.update()

    # 키보드 입력 처리
    def key_press(self, event):
        
        # 1. 키 이벤트 중복 처리 방지
        self.canvas.events.key_press.block()
        ## 2D 이미지 입력 차단
        if self.images:
            self.img_canvas.events.key_press.block()
        
        # 2. 키 입력에 따른 동작 처리
        if event.key == 'N':
            self.offset += 1
            if self.offset >= self.total:
                self.offset = 0
            self.update_scan()

        elif event.key == 'B':
            self.offset -= 1
            if self.offset < 0:
                self.offset = self.total - 1
            self.update_scan()

        elif event.key == 'Q' or event.key == 'Escape':
            self.destroy()

    # 그리기 이벤트 처리
    def draw(self, event):
        # 장면 전환 시, 키보드 입력 차단 상태에서 활성화
        if self.canvas.events.key_press.blocked():
            self.canvas.events.key_press.unblock()
        # 이미지 창에서, 키보드 입력 차단 상태에서 활성화
        if self.images and self.img_canvas.events.key_press.blocked():
            self.img_canvas.events.key_press.unblock()

    # 시각화 종료
    def destroy(self):
        # 3D pointcloud
        self.canvas.close()
        # 2D 이미지
        if self.images:
            self.img_canvas.close()
        # vispy 종료
        vispy.app.quit()

    # 시각화 애플리케이션 실행
    def run(self):
        vispy.app.run()
