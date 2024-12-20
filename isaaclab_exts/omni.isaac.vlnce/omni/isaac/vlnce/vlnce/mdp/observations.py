# Copyright (c) 2023-2024, ETH Zurich (Robotics Systems Lab)
# Author: Pascal Roth
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""This sub-module contains observation terms specific for viplanner.

The functions can be passed to the :class:`omni.isaac.lab.managers.ObservationTermCfg` object to enable
the observation introduced by the function.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import os
import torch
import torch.nn.functional as F

from omni.isaac.lab.managers import SceneEntityCfg
from omni.isaac.lab.sensors import RayCaster
from omni.isaac.lab.sensors.camera import CameraData
from omni.isaac.lab.sensors.camera.utils import convert_orientation_convention
import omni.isaac.lab.utils.math as math_utils
from omni.isaac.lab.assets import Articulation, RigidObject

from .actions import NavigationAction, VLMActions, VLMActionsGPT
import matplotlib.pyplot as plt
import cv2

if TYPE_CHECKING:
    from omni.isaac.lab.envs.base_env import BaseEnv
    from omni.isaac.lab.envs import ManagerBasedEnv


def matterport_raycast_camera_data(env: BaseEnv, sensor_cfg: SceneEntityCfg, data_type: str) -> torch.Tensor:
    """Images generated by the raycast camera."""
    # extract the used quantities (to enable type-hinting)
    sensor: CameraData = env.scene.sensors[sensor_cfg.name].data

    # return the data
    if data_type == "distance_to_image_plane":
        output = sensor.output[data_type].clone().unsqueeze(1)
        output[torch.isnan(output)] = 0.0
        output[torch.isinf(output)] = 0.0
        return output
    else:
        return sensor.output[data_type].clone().permute(0, 3, 1, 2)

def isaac_camera_data(env: BaseEnv, sensor_cfg: SceneEntityCfg, data_type: str) -> torch.Tensor:
    """Images generated by the usd camera."""
    # extract the used quantities (to enable type-hinting)
    sensor: CameraData = env.scene.sensors[sensor_cfg.name].data

    # import ipdb; ipdb.set_trace()
    # return the data
    if data_type == "distance_to_image_plane":
        output = sensor.output[data_type].clone().unsqueeze(1)
        output[torch.isnan(output)] = 0.0
        output[torch.isinf(output)] = 0.0
        # output = torch.clip(output, 0.0, 10.0)
        # near_clip = 0.0
        # far_clip = 10.0
        # output = (output - near_clip) / (far_clip - near_clip)  - 0.5
        # depth_image_size = (output.shape[2], output.shape[3])
        # output_clone = output.clone().reshape(env.num_envs, depth_image_size[0], depth_image_size[1])[0,:,:]
        # window_name = "Depth Image"
        # cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        # cv2.imshow("Depth Image", output_clone.cpu().numpy())
        # cv2.waitKey(1)
        return output
    else:
        # import ipdb; ipdb.set_trace()
        rgb_image = sensor.output[data_type].clone().cpu().numpy()[0,:,:,:]
        # # depth_image_size = (output.shape[2], output.shape[3])
        # output_clone = output.clone().reshape(env.num_envs, depth_image_size[0], depth_image_size[1])[0,:,:]
        # window_name = "RGB Image"
        # cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        # cv2.imshow(window_name, rgb_image)
        # cv2.waitKey(1)
        return sensor.output[data_type].clone()

def process_depth_image(env: BaseEnv, sensor_cfg: SceneEntityCfg, data_type: str, visualize=False, far_clip: float=5.0, near_clip: float=0.3) -> torch.Tensor:
    """Process the depth image."""
    # import ipdb; ipdb.set_trace()
    # extract the used quantities (to enable type-hinting)
    sensor: CameraData = env.scene.sensors[sensor_cfg.name].data

    output = sensor.output[data_type].clone().unsqueeze(1)
    # # output = output[:,:, :-2, 4:-4]
    # near_clip = 0.3
    # far_clip = 5.0
    # import pdb; pdb.set_trace()
    output[torch.isnan(output)] = far_clip
    output[torch.isinf(output)] = far_clip

    # depth_image_size = (output.shape[2], output.shape[3])
    # output_clone = output.clone().reshape(env.num_envs, depth_image_size[0], depth_image_size[1])[0,:,:]
    # window_name = "Before clipping"
    # import pdb; pdb.set_trace()
    # cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    # cv2.imshow(window_name, output_clone.cpu().numpy())
    # cv2.waitKey(1)

    
    # output = torch.clip(output, near_clip, far_clip)
    # output = output - near_clip
    # output = F.interpolate(output, size=(53, 30), mode='nearest')
    # depth_image_size = (output.shape[2], output.shape[3])
    # output_clone = output.clone().reshape(env.num_envs, depth_image_size[0], depth_image_size[1])[0,:,:]
    # window_name = "after clipping and normalization"
    # cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    # cv2.imshow(window_name, output_clone.cpu().numpy())
    # cv2.waitKey(1)


    # process_depth_feature = env.action_manager._terms['paths'].depth_cnn(output)
    # print("depth shape: ", output.reshape(env.num_envs, -1).shape)
    # import ipdb; ipdb.set_trace()
    # path = "/home/yji/Biped/biped_vision/depth_image/"
    # path=os.path.join(path, str(env.action_manager._terms['paths'].image_count)+".png")
    # import ipdb; ipdb.set_trace()
    if visualize:
        depth_image_size = (output.shape[2], output.shape[3])
        output_clone = output.clone().reshape(env.num_envs, depth_image_size[0], depth_image_size[1])[0,:,:]
        window_name = "Depth Image"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.imshow("Depth Image", output_clone.cpu().numpy())
        cv2.waitKey(1)

    # plt.imsave(path, output_clone.cpu().numpy(), cmap="gray")
    # import pdb; pdb.set_trace()
    # print(output)
    return output

def process_lidar(env: BaseEnv, sensor_cfg: SceneEntityCfg, offset: float = 0.5) -> torch.Tensor:
    """Process the lidar input."""
    # import ipdb; ipdb.set_trace()
    sensor: RayCaster = env.scene.sensors[sensor_cfg.name]
    # import pdb; pdb.set_trace()
    output = sensor.data.pos_w[:, 2].unsqueeze(1) - sensor.data.ray_hits_w[..., 2] - offset
    near_clip = 0.0
    far_clip = 5.0
    output[torch.isnan(output)] = far_clip
    output[torch.isinf(output)] = far_clip
    output = torch.clip(output, near_clip, far_clip)
    output = (output - near_clip) / (far_clip - near_clip)  - 0.5
    return output.reshape(env.num_envs, -1)


def cam_int_matrix(env: BaseEnv, sensor_cfg: SceneEntityCfg) -> torch.Tensor:
    """Intrinsic matrix of the camera."""
    # extract the used quantities (to enable type-hinting)
    sensor: CameraData = env.scene.sensors[sensor_cfg.name].data
    
    return sensor.intrinsic_matrices.clone().reshape(-1,9)

def cam_position(env: BaseEnv, sensor_cfg: SceneEntityCfg) -> torch.Tensor:
    """Position of the camera."""
    # extract the used quantities (to enable type-hinting)
    sensor: CameraData = env.scene.sensors[sensor_cfg.name].data

    return sensor.pos_w.clone()

def cam_orientation(env: BaseEnv, sensor_cfg: SceneEntityCfg) -> torch.Tensor:
    """Orientation of the camera."""
    # extract the used quantities (to enable type-hinting)
    sensor: CameraData = env.scene.sensors[sensor_cfg.name].data

    return sensor.quat_w_world.clone()

def cam_orientation_ros(env: BaseEnv, sensor_cfg: SceneEntityCfg) -> torch.Tensor:
    """Orientation of the camera."""
    # extract the used quantities (to enable type-hinting)
    sensor: CameraData = env.scene.sensors[sensor_cfg.name].data
    return convert_orientation_convention(sensor.quat_w_world, origin="world", target="ros")
    # return sensor.quat_w_world.clone()

def low_level_actions(env: BaseEnv) -> torch.Tensor:
    """Low-level actions."""
    # extract the used quantities (to enable type-hinting)
    action_term: NavigationAction = env.action_manager._terms['paths']

    return action_term.low_level_actions.clone()

def low_level_actions_llava(env: BaseEnv) -> torch.Tensor:
    """Low-level actions."""
    # extract the used quantities (to enable type-hinting)
    action_term: VLMActions = env.action_manager._terms['vlm_actions']

    return action_term.low_level_actions.clone()

def low_level_actions_gpt(env: BaseEnv) -> torch.Tensor:
    """Low-level actions."""
    # extract the used quantities (to enable type-hinting)
    action_term: VLMActionsGPT = env.action_manager._terms['vlm_actions_gpt']

    return action_term.low_level_actions.clone()

def last_low_level_actions(env: BaseEnv, action_name: str | None = None) -> torch.Tensor:

    """Low-level actions."""
    # extract the used quantities (to enable type-hinting)
    action_term: NavigationAction = env.action_manager._terms['paths']

    return action_term.low_level_actions.clone()

def last_low_level_actions_llava(env: BaseEnv, action_name: str | None = None) -> torch.Tensor:

    """Low-level actions."""
    # extract the used quantities (to enable type-hinting)
    action_term: VLMActions = env.action_manager._terms['vlm_actions']

    return action_term.low_level_actions.clone()

def last_low_level_actions_gpt(env: BaseEnv, action_name: str | None = None) -> torch.Tensor:

    """Low-level actions."""
    # extract the used quantities (to enable type-hinting)
    action_term: VLMActionsGPT = env.action_manager._terms['vlm_actions_gpt']

    return action_term.low_level_actions.clone()

def last_mid_actions(env: BaseEnv, action_name: str | None = None) -> torch.Tensor:
    """The last input action to the environment.

    The name of the action term for which the action is required. If None, the
    entire action tensor is returned.
    """
    if action_name is None:
        return env.action_manager.action
    else:
        return env.action_manager.get_term(action_name).raw_actions

def base_lin_acc(env: BaseEnv, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")) -> torch.Tensor:
    """Root linear velocity in the asset's root frame."""
    # extract the used quantities (to enable type-hinting)
    asset: RigidObject = env.scene[asset_cfg.name]
    lin_acc_w = asset.data.body_lin_acc_w[:, asset_cfg.body_ids[0], :]
    lin_acc_b = math_utils.quat_rotate_inverse(
            asset.data.root_quat_w, lin_acc_w
        )
    return lin_acc_b


def base_ang_acc(env: BaseEnv, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")) -> torch.Tensor:
    """Root angular velocity in the asset's root frame."""
    # extract the used quantities (to enable type-hinting)
    asset: RigidObject = env.scene[asset_cfg.name]
    ang_acc_w = asset.data.body_ang_acc_w[:, asset_cfg.body_ids[0], :]
    ang_acc_b = math_utils.quat_rotate_inverse(
            asset.data.root_quat_w, ang_acc_w
        )
    return ang_acc_b


def base_rpy(env: ManagerBasedEnv, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")) -> torch.Tensor:
    """Root rotation in the asset's root frame."""
    # extract the used quantities (to enable type-hinting)
    asset: RigidObject = env.scene[asset_cfg.name]
    root_quat_w = asset.data.root_quat_w

    qw = root_quat_w[:, 0]
    qx = root_quat_w[:, 1]
    qy = root_quat_w[:, 2]
    qz = root_quat_w[:, 3]

    # Roll (x-axis rotation)
    roll = torch.atan2(2 * (qw * qx + qy * qz), 1 - 2 * (qx * qx + qy * qy))

    # Pitch (y-axis rotation)
    sinp = 2 * (qw * qy - qz * qx)
    pitch = torch.where(torch.abs(sinp) < 1, torch.asin(sinp), torch.sign(sinp) * (torch.tensor(torch.pi) / 2))

    # Yaw (z-axis rotation)
    yaw = torch.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))

    return torch.stack((roll, pitch, yaw), dim=1)


# Define voxel grid parameters
voxel_size_xy = 0.06  # Voxel size in the x and y dimensions
range_x = [-0.8, 0.2+1e-9]
# range_y = [-1.0 + 0.05, 1.0 + 0.05]
range_y = [-0.8, 0.8+1e-9]
range_z = [0.0, 5.0]

from collections import deque
# Create a deque with a maximum length of 10
prev_height_maps = deque(maxlen=10)

def height_map_lidar(env: ManagerBasedEnv, sensor_cfg: SceneEntityCfg, offset: float = 0.5) -> torch.Tensor:
    """Height scan from the given sensor w.r.t. the sensor's frame.

    The provided offset (Defaults to 0.5) is subtracted from the returned values.
    """
    # global prev_height_maps

    # extract the used quantities (to enable type-hinting)
    sensor: RayCaster = env.scene.sensors[sensor_cfg.name]

    hit_vec = sensor.data.ray_hits_w - sensor.data.pos_w.unsqueeze(1)
    hit_vec[torch.isinf(hit_vec)] = 0.0
    hit_vec[torch.isnan(hit_vec)] = 0.0
    
    hit_vec_shape = hit_vec.shape
    hit_vec = hit_vec.view(-1, hit_vec.shape[-1])
    robot_base_quat_w = env.scene["robot"].data.root_quat_w
    sensor_quat_default = torch.tensor([-0.131, 0.0, -0.991, 0.0], device=robot_base_quat_w.device).unsqueeze(0).repeat(hit_vec_shape[0], 1)
    sensor_quat_w = math_utils.quat_mul(robot_base_quat_w, sensor_quat_default)
    quat_w_dup = (sensor_quat_w.unsqueeze(1).repeat(1, hit_vec_shape[1], 1)).view(-1, sensor_quat_w.shape[-1])
    hit_vec_lidar_frame = math_utils.quat_rotate_inverse(quat_w_dup, hit_vec)
    hit_vec_lidar_frame = hit_vec_lidar_frame.view(hit_vec_shape[0], hit_vec_shape[1], hit_vec_lidar_frame.shape[-1])

    num_envs = hit_vec_lidar_frame.shape[0]

    # Calculate the number of voxels in each dimension
    x_bins = torch.arange(range_x[0], range_x[1], voxel_size_xy, device=hit_vec_lidar_frame.device)
    y_bins = torch.arange(range_y[0], range_y[1], voxel_size_xy, device=hit_vec_lidar_frame.device)

    x = hit_vec_lidar_frame[..., 0]
    y = hit_vec_lidar_frame[..., 1]
    z = hit_vec_lidar_frame[..., 2]
    
    valid_indices = (x > range_x[0]) & (x <= range_x[1]) & \
                    (y > range_y[0]) & (y <= range_y[1]) & \
                    (z >= range_z[0]) & (z <= range_z[1])

    x_filtered = x[valid_indices]
    y_filtered = y[valid_indices]
    z_filtered = z[valid_indices]

    x_indices = torch.bucketize(x_filtered, x_bins) - 1
    y_indices = torch.bucketize(y_filtered, y_bins) - 1

    env_indices = torch.arange(num_envs, device=hit_vec_lidar_frame.device).unsqueeze(1).expand_as(valid_indices)
    flat_env_indices = env_indices[valid_indices]

    map_2_5D = torch.full((num_envs, len(x_bins), len(y_bins)), float('inf'), device=hit_vec_lidar_frame.device)
    linear_indices = flat_env_indices * len(x_bins) * len(y_bins) + x_indices * len(y_bins) + y_indices

    # Subtract the offset and apply dropout
    # if torch.any(linear_indices < 0) or torch.any(linear_indices >= map_2_5D.view(-1).size(0)):
    #     print("Index out of bounds")
    #     print("linear_indices: ", linear_indices)
    #     print("map_2_5D: ", map_2_5D)
    #     import pdb; pdb.set_trace()
    # assert torch.all(linear_indices >= 0) and torch.all(linear_indices < map_2_5D.view(-1).size(0)), "Index out of bounds"
    map_2_5D = map_2_5D.view(-1).scatter_reduce_(0, linear_indices, z_filtered, reduce="amin") - offset
    map_2_5D = torch.where(map_2_5D < 0.05, torch.tensor(0.0, device=map_2_5D.device), map_2_5D)

    # # Append the cloned map to the deque
    # prev_height_maps.append(map_2_5D.clone())
    # height_maps_hist = list(prev_height_maps)

    # Calculate the maximum value for each pixel across the last ten frames
    map_2_5D = torch.where(torch.isinf(map_2_5D), torch.tensor(0.0, device=map_2_5D.device), map_2_5D)
    # Apply maximum pooling with a kernel size of 3
    # if len(map_2_5D.shape) == 2:
    #     map_2_5D = map_2_5D.unsqueeze(0)
    # import pdb; pdb.set_trace()
    map_2_5D = map_2_5D.view(num_envs, len(x_bins), len(y_bins))
    max_across_frames = F.max_pool2d(map_2_5D, kernel_size=3, stride=1, padding=1).view(num_envs, -1)

    
    # # # # import pdb; pdb.set_trace()
    # # # # # Reshape map_2_5D to 2D image
    # image = map_2_5D[0].cpu().numpy().reshape(len(x_bins), len(y_bins))

    # # # Visualization (optional)
    # image = max_across_frames[0].cpu().numpy().reshape(len(x_bins), len(y_bins))

    # # image = (image * 255).astype(int)
    # image = image.astype('uint8')

    # cv2.imshow("Height Map", image)
    # cv2.waitKey(1)
    # cv2.destroyAllWindows()

    # output = (max_across_frames * (torch.rand(map_2_5D.shape, device=map_2_5D.device) > 0.05))

    # print("output: ", output)

    return max_across_frames

