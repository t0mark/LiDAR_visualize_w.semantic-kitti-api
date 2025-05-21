#!/usr/bin/env python3
# This file is covered by the LICENSE file in the root of this project.

import argparse
import os
import yaml
from auxiliary.laserscan import LaserScan, SemLaserScan
from auxiliary.laserscanvis import LaserScanVis

if __name__ == '__main__':
    parser = argparse.ArgumentParser("./visualize.py")
    parser.add_argument(
        '--dataset', '-d',
        type=str,
        required=True,
        help='LiDAR 데이터 시각화',
    )
    parser.add_argument(
        '--config', '-c',
        type=str,
        required=False,
        default="config/semantic-kitti.yaml",
        help='데이터셋 설정 파일',
    )
    parser.add_argument(
        '--open-data',
        type=str,
        dest='open_data',
        required=False,
        default="",
        help='오픈 데이터셋 지정',
    )
    parser.add_argument(
        '--ignore-label', '-i',
        dest='ignore_label',
        default=False,
        action='store_true',
        help='Label 데이터 없이, LiDAR 데이터만 사용',
    )
    parser.add_argument(
        '--predictions',
        dest='predictions',
        default=False,
        required=False,
        action='store_true',
        help='[x, y, z, intensity, label] 형태의 데이터 사용'
    )
    parser.add_argument(
        '--mapping',
        dest='mapping',
        default=False,
        required=False,
        action='store_true',
        help='특정 클래스만 표현 (YAML 파일의 label_map 사용)'
    )
    FLAGS, unparsed = parser.parse_known_args()

    # 옵션 출력
    print("*" * 80)
    print("INTERFACE:")
    print("Dataset", FLAGS.dataset)
    print("Config", FLAGS.config)
    print("*" * 80)

    # 설정 파일 열기
    try:
        print("설정 파일: %s" % FLAGS.config)
        CFG = yaml.safe_load(open(FLAGS.config, 'r'))
    except Exception as e:
        print(e)
        print("YAML 파일 오류")
        quit()
    
    # 절대 설정 파일 (항상 사용)
    try:
        absolutely_CFG = yaml.safe_load(open('config/absolutely-config.yaml', 'r'))
    except Exception as e:
        print(e)
        print("absolutely-YAML 파일 오류")
        quit()

    # LiDAR 폴더 확인
    if FLAGS.predictions:
        scan_paths = os.path.join(FLAGS.dataset, "predictions")
    else:
        scan_paths = os.path.join(FLAGS.dataset, CFG["lidar"]["manufacturer"])
    if os.path.isdir(scan_paths):
        print(f"{scan_paths} 사용 중...")
    else:
        print(f"{scan_paths} 존재하지 않습니다! 종료 중...")
        quit()

    # pointcloud 파일 목록 가져오기
    scan_names = [os.path.join(dp, f) for dp, dn, fn in os.walk(os.path.expanduser(scan_paths)) for f in fn]
    scan_names.sort()

    # label 폴더 확인
    if FLAGS.predictions:
        # predictions 모드
        print("predictions mode: [x, y, z, intensity, label] 형식 사용")
        label_names = []
    else:
        # labels 폴더 사용
        label_paths = os.path.join(FLAGS.dataset, "labels")
        if os.path.isdir(label_paths):
            print(f"{label_paths} 사용 중...")
        else:
            print(f"{label_paths} 존재하지 않습니다! 종료 중...")
            quit()
        
        # label 파일 목록 가져오기
        label_names = [os.path.join(dp, f) for dp, dn, fn in os.walk(os.path.expanduser(label_paths)) for f in fn]
        label_names.sort()

    # scan 객체 생성
    ## color_dict 설정
    if FLAGS.mapping:
        # mapping 모드: 원본 label -> [unlabeld, road, sidewalk, car, other-vehicle]
        color_dict = absolutely_CFG["mapping_color_map"]
        if FLAGS.open_data:
            label_map = absolutely_CFG[FLAGS.open_data]["label_map"]
        else:
            label_map = CFG["label_map"]
    else:
        # 일반 모드: 원본 label 사용
        if FLAGS.open_data:
            color_dict = absolutely_CFG[FLAGS.open_data]["color_map"]
        else:
            color_dict = CFG["color_map"]
    
    # LiDAR 정보 설정
    lidar = CFG["lidar"]

    scan = SemLaserScan(
        sem_color_dict=color_dict,
        project=True, 
        H=lidar["H"], 
        W=lidar["W"], 
        fov_up=lidar["fov_up"], 
        fov_down=lidar["fov_down"]
    )
    scan.set_combined(FLAGS.predictions)
    scan.set_mapping(FLAGS.mapping)
    if FLAGS.mapping:
        scan.set_label_map(label_map)

    # visualizer 객체 생성
    vis = LaserScanVis(
        scan=scan,
        scan_names=scan_names,
        label_names=label_names,
        label = not FLAGS.ignore_label,
        predictions=FLAGS.predictions,
        mapping=FLAGS.mapping
    )
    
    # 조작어 출력
    print("To navigate:")
    print("\tb: back (previous scan)")
    print("\tn: next (next scan)")
    print("\tq: quit (exit program)")

    # 실행
    vis.run()