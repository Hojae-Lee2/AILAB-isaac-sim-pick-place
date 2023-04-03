# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from omni.isaac.kit import SimulationApp

simulation_app = SimulationApp({"headless": False})

from omni.isaac.core import World
from omni.isaac.manipulators import SingleManipulator
from omni.isaac.manipulators.grippers import ParallelGripper
from omni.isaac.core.utils.stage import add_reference_to_stage, get_current_stage
from omni.isaac.core.utils.prims import create_prim, delete_prim
from omni.isaac.core.utils.semantics import add_update_semantics
from omni.isaac.core.utils.extensions import get_extension_path_from_name
from pick_place_controller import PickPlaceController
from omni.isaac.core.objects import DynamicCuboid
from omni.isaac.sensor import Camera
from omni.isaac.core.prims.xform_prim import XFormPrim
import omni.kit.commands
import carb
import sys
import numpy as np
import argparse
import os
import matplotlib.pyplot as plt
import cv2
from PIL import Image
import random

parser = argparse.ArgumentParser()
parser.add_argument("--test", default=False, action="store_true", help="Run in test mode")
args, unknown = parser.parse_known_args()

my_world = World(stage_units_in_meters=1.0)
my_world.scene.add_default_ground_plane()

ur5e_usd_path = "/home/ailab/Workspace/minhwan/isaac_sim-2022.2.0/github_my/isaac-sim-pick-place/ur5e_handeye_gripper.usd"
if os.path.isfile(ur5e_usd_path):
    pass
else:
    raise Exception(f"{ur5e_usd_path} not found")

add_reference_to_stage(usd_path=ur5e_usd_path, prim_path="/World/UR5e")
gripper = ParallelGripper(
    end_effector_prim_path="/World/UR5e/right_inner_finger_pad",
    joint_prim_names=["left_outer_knuckle_joint", "right_outer_knuckle_joint"],
    joint_opened_positions=np.array([0.0, 0.0]),
    joint_closed_positions=np.array([np.pi*2/9, -np.pi*2/9]),
    action_deltas=np.array([-np.pi*2/9, np.pi*2/9]),
)
my_ur5e = my_world.scene.add(
    SingleManipulator(
        prim_path="/World/UR5e", name="my_ur5e", end_effector_prim_name="right_inner_finger_pad", gripper=gripper
    )
)
# my_ur5e.set_joints_default_state(
#     positions=np.array([-np.pi / 2, -np.pi / 2, -np.pi / 2, -np.pi / 2, np.pi / 2, 0])
# )
rgb_camera = Camera(
    prim_path="/World/UR5e/realsense/RGB",
    frequency=20,
    resolution=(1920, 1080),
)
depth_camera = Camera(
    prim_path="/World/UR5e/realsense/Depth",
    frequency=20,
    resolution=(1920, 1080),
)

##########
#Add cube
###########
size_scale = 0.03
# size_scale_z = 0.03
# cube = my_world.scene.add(
#     DynamicCuboid(
#         name="cube",
#         position=np.array([0.4, 0.33, 0.1 + size_scale/2]),
#         prim_path="/World/Cube",
#         scale=np.array([size_scale, size_scale, size_scale]),
#         size=1.0,
#         color=np.array([1, 0, 1]),
#         mass=0
#     )
# )

#######
#Add ycb object
#########
# Setting up import configuration:
status, import_config = omni.kit.commands.execute("URDFCreateImportConfig")
import_config.merge_fixed_joints = False
import_config.convex_decomp = False
import_config.import_inertia_tensor = True
import_config.fix_base = False
import_config.make_default_prim = True
import_config.self_collision = False
import_config.create_physics_scene = True
import_config.import_inertia_tensor = False
# import_config.default_drive_strength = 1047.19751
# import_config.default_position_drive_damping = 52.35988
# import_config.default_drive_type = _urdf.UrdfJointTargetType.JOINT_DRIVE_POSITION

import_config.distance_scale = 0.1
path = '/home/nam/workspace/preprocessed_ycb'
objects = os.listdir(path)
# for i in range(3):
a = random.randint(0, len(objects))
print(objects[a])
ycb_file = os.path.join(path, objects[a], 'raw_mesh.urdf')
# Import URDF, stage_path contains the path the path to the usd prim in the stage.
status, stage_path = omni.kit.commands.execute(
    "URDFParseAndImportFile",
    urdf_path = ycb_file,
    import_config=import_config,
)

ob = XFormPrim(stage_path)
# ob_scale = 
ob.set_world_pose(np.array([0, 0, 20]), np.array([1, 0, 0, 0]))
np.array([0.4, 0.33, 0.1 + size_scale/2])

my_world.scene.add_default_ground_plane()
my_ur5e.gripper.set_default_state(my_ur5e.gripper.joint_opened_positions)
my_world.reset()

# rgb_camera.initialize()
# depth_camera.initialize()
# rgb_camera.add_distance_to_camera_to_frame()
# rgb_camera.add_instance_segmentation_to_frame()
# rgb_camera.add_instance_id_segmentation_to_frame()
# rgb_camera.add_semantic_segmentation_to_frame()
# rgb_camera.add_bounding_box_2d_loose_to_frame()
# rgb_camera.add_bounding_box_2d_tight_to_frame()
# depth_camera.add_distance_to_camera_to_frame()

stage = get_current_stage()
cube_prim = stage.DefinePrim("/World/Cube")
add_update_semantics(prim=cube_prim, semantic_label="cube")

my_world.reset()

my_controller = PickPlaceController(
    name="pick_place_controller", gripper=my_ur5e.gripper, robot_articulation=my_ur5e, end_effector_initial_height=0.3
)
articulation_controller = my_ur5e.get_articulation_controller()

i = 0
while simulation_app.is_running():
    my_world.step(render=True)
    if my_world.is_playing():
        if my_world.current_time_step_index == 0:
            my_world.reset()
            my_controller.reset()
        # elif my_world.current_time_step_index == 200:
        if my_controller._event == 0:
            if my_controller._t >= 0.99:
            # if my_world.current_time_step_index > 110:
                my_controller.pause()
                # print(my_controller._t)
                # print(my_world.current_time_step_index)
                # rgb_image = rgb_camera.get_rgba()[:, :, :3]
                # depth_image = depth_camera.get_current_frame()["distance_to_camera"]
                # depth_image = rgb_camera.get_current_frame()["distance_to_camera"]
                # instance_segmentation_image = rgb_camera.get_current_frame()["instance_segmentation"]["data"]
                # loose_bbox = rgb_camera.get_current_frame()["bounding_box_2d_loose"]
                # tight_bbox = rgb_camera.get_current_frame()["bounding_box_2d_tight"]
                # print(loose_bbox)
                # print(tight_bbox)
                # print(np.unique(depth_image))
                
                # imgplot = plt.imshow(rgb_image)
                # plt.show()
                # inssegplot = plt.imshow(instance_segmentation_image)
                # plt.show()
                # depthplot = plt.imshow(depth_image)
                # plt.show()
                # print(depth_image.shape)
                # print(instance_segmentation_image.shape)
                # print(np.unique(depth_image))
                # print(type(depth_image[0][0]))
                # print(rgb_camera.get_world_pose())
                # print(rgb_camera.get_local_pose())
                
                # rgb_image = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2RGB)
                # instance_segmentation_image = np.array(instance_segmentation_image, dtype=type(depth_image[0][0]))
                # cv2.imwrite('/home/ailab/Workspace/minhwan/isaac_sim-2022.2.0/github_my/rgb_image_3.png', rgb_image)
                # # depth_image = depth_image.astype(np.uint8)
                # # cv2.imwrite('/home/nam/.local/share/ov/pkg/isaac_sim-2022.2.0/workspace/data/depth_image_3.png', depth_image*255)
                # depth_image = Image.fromarray((depth_image * 255.0).astype(np.uint8))
                # depth_image.save('/home/ailab/Workspace/minhwan/isaac_sim-2022.2.0/github_my/depth_image_3.png')
                # cv2.imwrite('/home/ailab/Workspace/minhwan/isaac_sim-2022.2.0/github_my/mask_3.png', instance_segmentation_image)
                
                # print(cube.get_local_pose()[0])
                
                my_controller.resume()
        # elif my_world.current_time_step_index > 210:
        observations = my_world.get_observations()
        actions = my_controller.forward(
            picking_position=np.array([pos_x,pos_y, 0.00]),
            placing_position=np.array([0.4, -0.33, 0.02]),
            current_joint_positions=my_ur5e.get_joint_positions(),
            end_effector_offset=np.array([0, 0, 0.25]),
        )
        if my_controller.is_done():
            print("done picking and placing")
        articulation_controller.apply_action(actions)
    if args.test is True:
        break


simulation_app.close()