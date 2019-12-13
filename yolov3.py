# coding:utf-8

import config as cfg
import numpy as np
import tensorflow as tf
from model.layers import *
from model.backbone.MobilenetV2 import MobilenetV2,MobilenetV2_dynamic
from utils import tools


class YOLOV3(object):
    def __init__(self, training):
        self.__training = training
        self.__classes = cfg.CLASSES
        # self.__num_classes = len(cfg.CLASSES)
        self.__num_classes = 0
        self.__strides = np.array(cfg.STRIDES)
        gt_per_grid = cfg.GT_PER_GRID
        self.__iou_loss_thresh = cfg.IOU_LOSS_THRESH
    def build_nework(self, input_data, val_reuse=False,gt_per_grid=3):
        """
        :param input_data: shape为(batch_size, input_size, input_size, 3)
        :return: conv_sbbox, conv_mbbox, conv_lbbox, pred_sbbox, pred_mbbox, pred_lbbox
        conv_sbbox的shape为(batch_size, input_size / 8, input_size / 8, gt_per_grid * (5 + num_classes))
        conv_mbbox的shape为(batch_size, input_size / 16, input_size / 16, gt_per_grid * (5 + num_classes))
        conv_lbbox的shape为(batch_size, input_size / 32, input_size / 32, gt_per_grid * (5 + num_classes))
        conv_?是YOLO的原始卷积输出(raw_dx, raw_dy, raw_dw, raw_dh, raw_conf, raw_prob)
        pred_sbbox的shape为(batch_size, input_size / 8, input_size / 8, gt_per_grid, 5 + num_classes)
        pred_mbbox的shape为(batch_size, input_size / 16, input_size / 16, gt_per_grid, 5 + num_classes)
        pred_lbbox的shape为(batch_size, input_size / 32, input_size / 32, gt_per_grid, 5 + num_classes)
        pred_?是YOLO预测bbox的信息(x, y, w, h, conf, prob)，(x, y, w, h)的大小是相对于input_size的
        """
        net_name = 'YoloV3'
        with tf.variable_scope(net_name, reuse=val_reuse):
            feature_map_s, feature_map_m, feature_map_l = MobilenetV2(input_data, self.__training)
            #jiangwei
            conv = convolutional(name='conv0', input_data=feature_map_l, filters_shape=(1, 1, 1280, 512),
                                 training=self.__training)
            conv = separable_conv(name='conv1', input_data=conv, input_c=512, output_c=1024, training=self.__training)
            conv = convolutional(name='conv2', input_data=conv, filters_shape=(1, 1, 1024, 512),
                                 training=self.__training)
            conv = separable_conv(name='conv3', input_data=conv, input_c=512, output_c=1024, training=self.__training)
            conv = convolutional(name='conv4', input_data=conv, filters_shape=(1, 1, 1024, 512),
                                 training=self.__training)

            # ----------**********---------- Detection branch of large object ----------**********----------
            conv_lbbox = separable_conv(name='conv5', input_data=conv, input_c=512, output_c=1024,
                                        training=self.__training)
            conv_lbbox = convolutional(name='conv6', input_data=conv_lbbox,
                                       filters_shape=(1, 1, 1024, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_lbbox = decode(name='pred_lbbox', conv_output=conv_lbbox,
                                num_classes=self.__num_classes, stride=self.__strides[2])
            # ----------**********---------- Detection branch of large object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv7', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training)
            conv = upsample(name='upsample0', input_data=conv)
            conv = route(name='route0', previous_output=feature_map_m, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional('conv8', input_data=conv, filters_shape=(1, 1, 96 + 256, 256),
                                 training=self.__training)
            conv = separable_conv('conv9', input_data=conv, input_c=256, output_c=512, training=self.__training)
            conv = convolutional('conv10', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training)
            conv = separable_conv('conv11', input_data=conv, input_c=256, output_c=512, training=self.__training)
            conv = convolutional('conv12', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training)

            # ----------**********---------- Detection branch of middle object ----------**********----------
            conv_mbbox = separable_conv(name='conv13', input_data=conv, input_c=256, output_c=512,
                                        training=self.__training)
            conv_mbbox = convolutional(name='conv14', input_data=conv_mbbox,
                                       filters_shape=(1, 1, 512, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_mbbox = decode(name='pred_mbbox', conv_output=conv_mbbox,
                                num_classes=self.__num_classes, stride=self.__strides[1])
            # ----------**********---------- Detection branch of middle object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv15', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)
            conv = upsample(name='upsample1', input_data=conv)
            conv = route(name='route1', previous_output=feature_map_s, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional(name='conv16', input_data=conv, filters_shape=(1, 1, 32 + 128, 128),
                                 training=self.__training)
            conv = separable_conv(name='conv17', input_data=conv, input_c=128, output_c=256, training=self.__training)
            conv = convolutional(name='conv18', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)
            conv = separable_conv(name='conv19', input_data=conv, input_c=128, output_c=256, training=self.__training)
            conv = convolutional(name='conv20', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)

            # ----------**********---------- Detection branch of small object ----------**********----------
            conv_sbbox = separable_conv(name='conv21', input_data=conv, input_c=128, output_c=256,
                                        training=self.__training)
            conv_sbbox = convolutional(name='conv22', input_data=conv_sbbox,
                                       filters_shape=(1, 1, 256, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_sbbox = decode(name='pred_sbbox', conv_output=conv_sbbox,
                                num_classes=self.__num_classes, stride=self.__strides[0])
            # ----------**********---------- Detection branch of small object ----------**********----------
        for var in tf.global_variables(net_name):
            tf.add_to_collection(net_name, var)
        return conv_sbbox, conv_mbbox, conv_lbbox, pred_sbbox, pred_mbbox, pred_lbbox
    def build_nework_slim(self, input_data, val_reuse=False,gt_per_grid=2):
        """
        :param input_data: shape为(batch_size, input_size, input_size, 3)
        :return: conv_sbbox, conv_mbbox, conv_lbbox, pred_sbbox, pred_mbbox, pred_lbbox
        conv_sbbox的shape为(batch_size, input_size / 8, input_size / 8, gt_per_grid * (5 + num_classes))
        conv_mbbox的shape为(batch_size, input_size / 16, input_size / 16, gt_per_grid * (5 + num_classes))
        conv_lbbox的shape为(batch_size, input_size / 32, input_size / 32, gt_per_grid * (5 + num_classes))
        conv_?是YOLO的原始卷积输出(raw_dx, raw_dy, raw_dw, raw_dh, raw_conf, raw_prob)
        pred_sbbox的shape为(batch_size, input_size / 8, input_size / 8, gt_per_grid, 5 + num_classes)
        pred_mbbox的shape为(batch_size, input_size / 16, input_size / 16, gt_per_grid, 5 + num_classes)
        pred_lbbox的shape为(batch_size, input_size / 32, input_size / 32, gt_per_grid, 5 + num_classes)
        pred_?是YOLO预测bbox的信息(x, y, w, h, conf, prob)，(x, y, w, h)的大小是相对于input_size的
        """
        net_name = 'YoloV3'
        with tf.variable_scope(net_name, reuse=val_reuse):
            feature_map_s, feature_map_m, feature_map_l = MobilenetV2(input_data, self.__training)

            conv = convolutional(name='conv0', input_data=feature_map_l, filters_shape=(1, 1, 1280, 256),
                                 training=self.__training)
            conv = separable_conv(name='conv1', input_data=conv, input_c=256, output_c=512, training=self.__training)
            conv = convolutional(name='conv2', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training)
            conv = separable_conv(name='conv3', input_data=conv, input_c=256, output_c=512, training=self.__training)
            conv = convolutional(name='conv4', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training)

            # ----------**********---------- Detection branch of large object ----------**********----------
            conv_lbbox = separable_conv(name='conv5', input_data=conv, input_c=256, output_c=512,
                                        training=self.__training)
            conv_lbbox = convolutional(name='conv6', input_data=conv_lbbox,
                                       filters_shape=(1, 1, 512, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_lbbox = decode(name='pred_lbbox', conv_output=conv_lbbox,
                                num_classes=self.__num_classes, stride=self.__strides[2])

            # ----------**********---------- Detection branch of large object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv7', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)
            conv = upsample(name='upsample0', input_data=conv)
            conv = route(name='route0', previous_output=feature_map_m, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional('conv8', input_data=conv, filters_shape=(1, 1, 96 + 128, 128),
                                 training=self.__training)
            conv = separable_conv('conv9', input_data=conv, input_c=128, output_c=256, training=self.__training)
            conv = convolutional('conv10', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)
            conv = separable_conv('conv11', input_data=conv, input_c=128, output_c=256, training=self.__training)
            conv = convolutional('conv12', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)

            # ----------**********---------- Detection branch of middle object ----------**********----------
            conv_mbbox = separable_conv(name='conv13', input_data=conv, input_c=128, output_c=256,
                                        training=self.__training)
            conv_mbbox = convolutional(name='conv14', input_data=conv_mbbox,
                                       filters_shape=(1, 1, 256, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_mbbox = decode(name='pred_mbbox', conv_output=conv_mbbox,
                                num_classes=self.__num_classes, stride=self.__strides[1])
            # ----------**********---------- Detection branch of middle object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv15', input_data=conv, filters_shape=(1, 1, 128, 64),
                                 training=self.__training)
            conv = upsample(name='upsample1', input_data=conv)
            conv = route(name='route1', previous_output=feature_map_s, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional(name='conv16', input_data=conv, filters_shape=(1, 1, 32 + 64, 64),
                                 training=self.__training)
            conv = separable_conv(name='conv17', input_data=conv, input_c=64, output_c=128, training=self.__training)
            conv = convolutional(name='conv18', input_data=conv, filters_shape=(1, 1, 128, 64),
                                 training=self.__training)
            conv = separable_conv(name='conv19', input_data=conv, input_c=64, output_c=128, training=self.__training)
            conv = convolutional(name='conv20', input_data=conv, filters_shape=(1, 1, 128, 64),
                                 training=self.__training)

            # ----------**********---------- Detection branch of small object ----------**********----------
            conv_sbbox = separable_conv(name='conv21', input_data=conv, input_c=64, output_c=128,
                                        training=self.__training)
            conv_sbbox = convolutional(name='conv22', input_data=conv_sbbox,
                                       filters_shape=(1, 1, 128, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_sbbox = decode(name='pred_sbbox', conv_output=conv_sbbox,
                                num_classes=self.__num_classes, stride=self.__strides[0])
            # ----------**********---------- Detection branch of small object ----------**********----------
        for var in tf.global_variables(net_name):
            tf.add_to_collection(net_name, var)
        return conv_sbbox, conv_mbbox, conv_lbbox, pred_sbbox, pred_mbbox, pred_lbbox
    def build_nework_slim_MNN(self, input_data, val_reuse=False,inputsize=544,gt_per_grid=2):
        """
        :param input_data: shape为(batch_size, input_size, input_size, 3)
        :return: conv_sbbox, conv_mbbox, conv_lbbox, pred_sbbox, pred_mbbox, pred_lbbox
        conv_sbbox的shape为(batch_size, input_size / 8, input_size / 8, gt_per_grid * (5 + num_classes))
        conv_mbbox的shape为(batch_size, input_size / 16, input_size / 16, gt_per_grid * (5 + num_classes))
        conv_lbbox的shape为(batch_size, input_size / 32, input_size / 32, gt_per_grid * (5 + num_classes))
        conv_?是YOLO的原始卷积输出(raw_dx, raw_dy, raw_dw, raw_dh, raw_conf, raw_prob)
        pred_sbbox的shape为(batch_size, input_size / 8, input_size / 8, gt_per_grid, 5 + num_classes)
        pred_mbbox的shape为(batch_size, input_size / 16, input_size / 16, gt_per_grid, 5 + num_classes)
        pred_lbbox的shape为(batch_size, input_size / 32, input_size / 32, gt_per_grid, 5 + num_classes)
        pred_?是YOLO预测bbox的信息(x, y, w, h, conf, prob)，(x, y, w, h)的大小是相对于input_size的
        """
        net_name = 'YoloV3'
        with tf.variable_scope(net_name, reuse=val_reuse):
            feature_map_s, feature_map_m, feature_map_l = MobilenetV2(input_data, self.__training)

            conv = convolutional(name='conv0', input_data=feature_map_l, filters_shape=(1, 1, 1280, 256),
                                 training=self.__training)
            conv = separable_conv(name='conv1', input_data=conv, input_c=256, output_c=512, training=self.__training)
            conv = convolutional(name='conv2', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training)
            conv = separable_conv(name='conv3', input_data=conv, input_c=256, output_c=512, training=self.__training)
            conv = convolutional(name='conv4', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training)

            # ----------**********---------- Detection branch of large object ----------**********----------
            conv_lbbox = separable_conv(name='conv5', input_data=conv, input_c=256, output_c=512,
                                        training=self.__training)
            conv_lbbox = convolutional(name='conv6', input_data=conv_lbbox,
                                       filters_shape=(1, 1, 512, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_lbbox = decode_validate(name='pred_lbbox', conv_output=conv_lbbox,
                                         num_classes=self.__num_classes, stride=self.__strides[2],
                                         shape=inputsize // 32, gt_pergrid=gt_per_grid)

            # ----------**********---------- Detection branch of large object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv7', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)
            conv = upsample_decode(name='upsample0', input_data=conv,shape1=inputsize//32,shape2=inputsize//32)
            conv = route(name='route0', previous_output=feature_map_m, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional('conv8', input_data=conv, filters_shape=(1, 1, 96 + 128, 128),
                                 training=self.__training)
            conv = separable_conv('conv9', input_data=conv, input_c=128, output_c=256, training=self.__training)
            conv = convolutional('conv10', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)
            conv = separable_conv('conv11', input_data=conv, input_c=128, output_c=256, training=self.__training)
            conv = convolutional('conv12', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)

            # ----------**********---------- Detection branch of middle object ----------**********----------
            conv_mbbox = separable_conv(name='conv13', input_data=conv, input_c=128, output_c=256,
                                        training=self.__training)
            conv_mbbox = convolutional(name='conv14', input_data=conv_mbbox,
                                       filters_shape=(1, 1, 256, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_mbbox = decode_validate(name='pred_mbbox', conv_output=conv_mbbox,
                                num_classes=self.__num_classes, stride=self.__strides[1],shape=inputsize//16,gt_pergrid=gt_per_grid)
            # ----------**********---------- Detection branch of middle object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv15', input_data=conv, filters_shape=(1, 1, 128, 64),
                                 training=self.__training)
            conv = upsample_decode(name='upsample1', input_data=conv,shape1=inputsize//16,shape2=inputsize//16)
            conv = route(name='route1', previous_output=feature_map_s, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional(name='conv16', input_data=conv, filters_shape=(1, 1, 32 + 64, 64),
                                 training=self.__training)
            conv = separable_conv(name='conv17', input_data=conv, input_c=64, output_c=128, training=self.__training)
            conv = convolutional(name='conv18', input_data=conv, filters_shape=(1, 1, 128, 64),
                                 training=self.__training)
            conv = separable_conv(name='conv19', input_data=conv, input_c=64, output_c=128, training=self.__training)
            conv = convolutional(name='conv20', input_data=conv, filters_shape=(1, 1, 128, 64),
                                 training=self.__training)

            # ----------**********---------- Detection branch of small object ----------**********----------
            conv_sbbox = separable_conv(name='conv21', input_data=conv, input_c=64, output_c=128,
                                        training=self.__training)
            conv_sbbox = convolutional(name='conv22', input_data=conv_sbbox,
                                       filters_shape=(1, 1, 128, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_sbbox = decode_validate(name='pred_sbbox', conv_output=conv_sbbox,
                                         num_classes=self.__num_classes, stride=self.__strides[0], shape=inputsize // 8,
                                         gt_pergrid=gt_per_grid)
            # ----------**********---------- Detection branch of small object ----------**********----------
            pred_sbbox = tf.reshape(pred_sbbox, (-1, 5 + self.__num_classes))
            pred_mbbox = tf.reshape(pred_mbbox, (-1, 5 + self.__num_classes))
            pred_lbbox = tf.reshape(pred_lbbox, (-1, 5 + self.__num_classes))
            pred_bbox = tf.concat([pred_sbbox, pred_mbbox, pred_lbbox], 0, name='output/boxconcat')
        for var in tf.global_variables(net_name):
            tf.add_to_collection(net_name, var)
        return pred_bbox
    def build_nework_MNN(self, input_data, val_reuse=False,inputsize=544,gt_per_grid=3,statedict=None):
        """
        :param input_data: shape为(batch_size, input_size, input_size, 3)
        :return: conv_sbbox, conv_mbbox, conv_lbbox, pred_sbbox, pred_mbbox, pred_lbbox
        conv_sbbox的shape为(batch_size, input_size / 8, input_size / 8, gt_per_grid * (5 + num_classes))
        conv_mbbox的shape为(batch_size, input_size / 16, input_size / 16, gt_per_grid * (5 + num_classes))
        conv_lbbox的shape为(batch_size, input_size / 32, input_size / 32, gt_per_grid * (5 + num_classes))
        conv_?是YOLO的原始卷积输出(raw_dx, raw_dy, raw_dw, raw_dh, raw_conf, raw_prob)
        pred_sbbox的shape为(batch_size, input_size / 8, input_size / 8, gt_per_grid, 5 + num_classes)
        pred_mbbox的shape为(batch_size, input_size / 16, input_size / 16, gt_per_grid, 5 + num_classes)
        pred_lbbox的shape为(batch_size, input_size / 32, input_size / 32, gt_per_grid, 5 + num_classes)
        pred_?是YOLO预测bbox的信息(x, y, w, h, conf, prob)，(x, y, w, h)的大小是相对于input_size的
        """
        net_name = 'YoloV3'
        with tf.variable_scope(net_name, reuse=val_reuse):
            feature_map_s, feature_map_m, feature_map_l = MobilenetV2(input_data, self.__training)

            conv = convolutional(name='conv0', input_data=feature_map_l, filters_shape=(1, 1, 1280, 512),
                                 training=self.__training)
            conv = separable_conv(name='conv1', input_data=conv, input_c=512, output_c=1024, training=self.__training)
            conv = convolutional(name='conv2', input_data=conv, filters_shape=(1, 1, 1024, 512),
                                 training=self.__training)
            conv = separable_conv(name='conv3', input_data=conv, input_c=512, output_c=1024, training=self.__training)
            conv = convolutional(name='conv4', input_data=conv, filters_shape=(1, 1, 1024, 512),
                                 training=self.__training)

            # ----------**********---------- Detection branch of large object ----------**********----------
            conv_lbbox = separable_conv(name='conv5', input_data=conv, input_c=512, output_c=1024,
                                        training=self.__training)
            conv_lbbox = convolutional(name='conv6', input_data=conv_lbbox,
                                       filters_shape=(1, 1, 1024, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_lbbox = decode_validate(name='pred_lbbox', conv_output=conv_lbbox,
                                num_classes=self.__num_classes, stride=self.__strides[2],shape=inputsize//32,gt_pergrid=gt_per_grid)
            # ----------**********---------- Detection branch of large object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv7', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training)
            conv = upsample_decode(name='upsample0', input_data=conv,shape1=inputsize//32,shape2=inputsize//32)
            conv = route(name='route0', previous_output=feature_map_m, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional('conv8', input_data=conv, filters_shape=(1, 1, 96 + 256, 256),
                                 training=self.__training)
            conv = separable_conv('conv9', input_data=conv, input_c=256, output_c=512, training=self.__training)
            conv = convolutional('conv10', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training)
            conv = separable_conv('conv11', input_data=conv, input_c=256, output_c=512, training=self.__training)
            conv = convolutional('conv12', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training)

            # ----------**********---------- Detection branch of middle object ----------**********----------
            conv_mbbox = separable_conv(name='conv13', input_data=conv, input_c=256, output_c=512,
                                        training=self.__training)
            conv_mbbox = convolutional(name='conv14', input_data=conv_mbbox,
                                       filters_shape=(1, 1, 512, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_mbbox = decode_validate(name='pred_mbbox', conv_output=conv_mbbox,
                                num_classes=self.__num_classes, stride=self.__strides[1],shape=inputsize//16,gt_pergrid=gt_per_grid)
            # ----------**********---------- Detection branch of middle object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv15', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)
            conv = upsample_decode(name='upsample1', input_data=conv,shape1=inputsize//16,shape2=inputsize//16)
            conv = route(name='route1', previous_output=feature_map_s, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional(name='conv16', input_data=conv, filters_shape=(1, 1, 32 + 128, 128),
                                 training=self.__training)
            conv = separable_conv(name='conv17', input_data=conv, input_c=128, output_c=256, training=self.__training)
            conv = convolutional(name='conv18', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)
            conv = separable_conv(name='conv19', input_data=conv, input_c=128, output_c=256, training=self.__training)
            conv = convolutional(name='conv20', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)

            # ----------**********---------- Detection branch of small object ----------**********----------
            conv_sbbox = separable_conv(name='conv21', input_data=conv, input_c=128, output_c=256,
                                        training=self.__training)
            conv_sbbox = convolutional(name='conv22', input_data=conv_sbbox,
                                       filters_shape=(1, 1, 256, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_sbbox = decode_validate(name='pred_sbbox', conv_output=conv_sbbox,
                                num_classes=self.__num_classes, stride=self.__strides[0],shape=inputsize//8,gt_pergrid=gt_per_grid)
            pred_sbbox = tf.reshape(pred_sbbox, (-1, 5+self.__num_classes))
            pred_mbbox = tf.reshape(pred_mbbox, (-1, 5+self.__num_classes))
            pred_lbbox = tf.reshape(pred_lbbox, (-1, 5+self.__num_classes))
            pred_bbox = tf.concat([pred_sbbox, pred_mbbox, pred_lbbox], 0,name='output/boxconcat')
        for var in tf.global_variables(net_name):
            tf.add_to_collection(net_name, var)
        return pred_bbox
        # return pred_sbbox,pred_mbbox,pred_lbbox

    def build_nework_slim_NMS(self, input_data, originH,originW,val_reuse=False,inputsize=544,thres=0.1,gt_per_grid=2):
        """
        :param input_data: shape为(batch_size, input_size, input_size, 3)
        :return: conv_sbbox, conv_mbbox, conv_lbbox, pred_sbbox, pred_mbbox, pred_lbbox
        conv_sbbox的shape为(batch_size, input_size / 8, input_size / 8, gt_per_grid * (5 + num_classes))
        conv_mbbox的shape为(batch_size, input_size / 16, input_size / 16, gt_per_grid * (5 + num_classes))
        conv_lbbox的shape为(batch_size, input_size / 32, input_size / 32, gt_per_grid * (5 + num_classes))
        conv_?是YOLO的原始卷积输出(raw_dx, raw_dy, raw_dw, raw_dh, raw_conf, raw_prob)
        pred_sbbox的shape为(batch_size, input_size / 8, input_size / 8, gt_per_grid, 5 + num_classes)
        pred_mbbox的shape为(batch_size, input_size / 16, input_size / 16, gt_per_grid, 5 + num_classes)
        pred_lbbox的shape为(batch_size, input_size / 32, input_size / 32, gt_per_grid, 5 + num_classes)
        pred_?是YOLO预测bbox的信息(x, y, w, h, conf, prob)，(x, y, w, h)的大小是相对于input_size的
        """
        net_name = 'YoloV3'
        with tf.variable_scope(net_name, reuse=val_reuse):
            feature_map_s, feature_map_m, feature_map_l = MobilenetV2(input_data, self.__training)

            conv = convolutional(name='conv0', input_data=feature_map_l, filters_shape=(1, 1, 1280, 256),
                                 training=self.__training)
            conv = separable_conv(name='conv1', input_data=conv, input_c=256, output_c=512, training=self.__training)
            conv = convolutional(name='conv2', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training)
            conv = separable_conv(name='conv3', input_data=conv, input_c=256, output_c=512, training=self.__training)
            conv = convolutional(name='conv4', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training)

            # ----------**********---------- Detection branch of large object ----------**********----------
            conv_lbbox = separable_conv(name='conv5', input_data=conv, input_c=256, output_c=512,
                                        training=self.__training)
            conv_lbbox = convolutional(name='conv6', input_data=conv_lbbox,
                                       filters_shape=(1, 1, 512, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_lbbox = decode_nms(name='pred_lbbox', conv_output=conv_lbbox,
                                    num_classes=self.__num_classes, stride=self.__strides[2], shape=inputsize // 32,
                                    gt_pergrid=gt_per_grid, originW=originW, originH=originH,
                                    inputsize=inputsize)

            # ----------**********---------- Detection branch of large object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv7', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)
            conv = upsample(name='upsample0', input_data=conv)
            conv = route(name='route0', previous_output=feature_map_m, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional('conv8', input_data=conv, filters_shape=(1, 1, 96 + 128, 128),
                                 training=self.__training)
            conv = separable_conv('conv9', input_data=conv, input_c=128, output_c=256, training=self.__training)
            conv = convolutional('conv10', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)
            conv = separable_conv('conv11', input_data=conv, input_c=128, output_c=256, training=self.__training)
            conv = convolutional('conv12', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)

            # ----------**********---------- Detection branch of middle object ----------**********----------
            conv_mbbox = separable_conv(name='conv13', input_data=conv, input_c=128, output_c=256,
                                        training=self.__training)
            conv_mbbox = convolutional(name='conv14', input_data=conv_mbbox,
                                       filters_shape=(1, 1, 256, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_mbbox = decode_nms(name='pred_mbbox', conv_output=conv_mbbox,
                                    num_classes=self.__num_classes, stride=self.__strides[1], shape=inputsize // 16,
                                    gt_pergrid=gt_per_grid, originW=originW, originH=originH,
                                    inputsize=inputsize)

            # ----------**********---------- Detection branch of middle object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv15', input_data=conv, filters_shape=(1, 1, 128, 64),
                                 training=self.__training)
            conv = upsample(name='upsample1', input_data=conv)
            conv = route(name='route1', previous_output=feature_map_s, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional(name='conv16', input_data=conv, filters_shape=(1, 1, 32 + 64, 64),
                                 training=self.__training)
            conv = separable_conv(name='conv17', input_data=conv, input_c=64, output_c=128, training=self.__training)
            conv = convolutional(name='conv18', input_data=conv, filters_shape=(1, 1, 128, 64),
                                 training=self.__training)
            conv = separable_conv(name='conv19', input_data=conv, input_c=64, output_c=128, training=self.__training)
            conv = convolutional(name='conv20', input_data=conv, filters_shape=(1, 1, 128, 64),
                                 training=self.__training)

            # ----------**********---------- Detection branch of small object ----------**********----------
            conv_sbbox = separable_conv(name='conv21', input_data=conv, input_c=64, output_c=128,
                                        training=self.__training)
            conv_sbbox = convolutional(name='conv22', input_data=conv_sbbox,
                                       filters_shape=(1, 1, 128, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_sbbox = decode_nms(name='pred_sbbox', conv_output=conv_sbbox,
                                    num_classes=self.__num_classes, stride=self.__strides[0], shape=inputsize // 8,
                                    gt_pergrid=gt_per_grid, originW=originW, originH=originH,
                                    inputsize=inputsize)

            # ----------**********---------- Detection branch of small object ----------**********----------
        pred_sbbox = tf.reshape(pred_sbbox, (-1, 5 + self.__num_classes))
        pred_mbbox = tf.reshape(pred_mbbox, (-1, 5 + self.__num_classes))
        pred_lbbox = tf.reshape(pred_lbbox, (-1, 5 + self.__num_classes))
        pred_bbox = tf.concat([pred_sbbox, pred_mbbox, pred_lbbox], 0)
        yxyx, conf = tf.split(pred_bbox, [4, 1], axis=1)
        conf = tf.squeeze(conf, squeeze_dims=1)
        mask = tf.greater_equal(conf, tf.constant(thres))
        filterboxes = tf.boolean_mask(yxyx, mask)
        filterscores = tf.boolean_mask(conf, mask)

        nms_idx = tf.image.non_max_suppression(boxes=filterboxes, scores=filterscores, max_output_size=100,
                                               iou_threshold=0.45)
        nmsboxes = tf.gather(filterboxes, nms_idx)
        nmsscores = tf.gather(filterscores, nms_idx)
        nmsscores = tf.expand_dims(nmsscores, axis=1)
        ymin, xmin, ymax, xmax = tf.split(nmsboxes, [1, 1, 1, 1], 1)
        nmsboxes = tf.concat([xmin, ymin, xmax, ymax], 1)

        pred_bbox = tf.concat([nmsboxes, nmsscores], 1, name='output/boxconcat')
        for var in tf.global_variables(net_name):
            tf.add_to_collection(net_name, var)
        return pred_bbox
    def build_nework_NMS(self, input_data, originH,originW,val_reuse=False,inputsize=544,thres=0.1,iouthres=0.5,gt_per_grid=3):
        """
        :param input_data: shape为(batch_size, input_size, input_size, 3)
        :return: conv_sbbox, conv_mbbox, conv_lbbox, pred_sbbox, pred_mbbox, pred_lbbox
        conv_sbbox的shape为(batch_size, input_size / 8, input_size / 8, gt_per_grid * (5 + num_classes))
        conv_mbbox的shape为(batch_size, input_size / 16, input_size / 16, gt_per_grid * (5 + num_classes))
        conv_lbbox的shape为(batch_size, input_size / 32, input_size / 32, gt_per_grid * (5 + num_classes))
        conv_?是YOLO的原始卷积输出(raw_dx, raw_dy, raw_dw, raw_dh, raw_conf, raw_prob)
        pred_sbbox的shape为(batch_size, input_size / 8, input_size / 8, gt_per_grid, 5 + num_classes)
        pred_mbbox的shape为(batch_size, input_size / 16, input_size / 16, gt_per_grid, 5 + num_classes)
        pred_lbbox的shape为(batch_size, input_size / 32, input_size / 32, gt_per_grid, 5 + num_classes)
        pred_?是YOLO预测bbox的信息(x, y, w, h, conf, prob)，(x, y, w, h)的大小是相对于input_size的
        """
        net_name = 'YoloV3'
        with tf.variable_scope(net_name, reuse=val_reuse):
            feature_map_s, feature_map_m, feature_map_l = MobilenetV2(input_data, self.__training)

            conv = convolutional(name='conv0', input_data=feature_map_l, filters_shape=(1, 1, 1280, 512),
                                 training=self.__training)
            conv = separable_conv(name='conv1', input_data=conv, input_c=512, output_c=1024, training=self.__training)
            conv = convolutional(name='conv2', input_data=conv, filters_shape=(1, 1, 1024, 512),
                                 training=self.__training)
            conv = separable_conv(name='conv3', input_data=conv, input_c=512, output_c=1024, training=self.__training)
            conv = convolutional(name='conv4', input_data=conv, filters_shape=(1, 1, 1024, 512),
                                 training=self.__training)

            # ----------**********---------- Detection branch of large object ----------**********----------
            conv_lbbox = separable_conv(name='conv5', input_data=conv, input_c=512, output_c=1024,
                                        training=self.__training)
            conv_lbbox = convolutional(name='conv6', input_data=conv_lbbox,
                                       filters_shape=(1, 1, 1024, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_lbbox = decode_nms(name='pred_lbbox', conv_output=conv_lbbox,
                                num_classes=self.__num_classes, stride=self.__strides[2],shape=inputsize//32,gt_pergrid=gt_per_grid,originW=originW,originH=originH,inputsize=inputsize)
            # ----------**********---------- Detection branch of large object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv7', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training)
            conv = upsample_decode(name='upsample0', input_data=conv,shape1=inputsize//32,shape2=inputsize//32)
            conv = route(name='route0', previous_output=feature_map_m, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional('conv8', input_data=conv, filters_shape=(1, 1, 96 + 256, 256),
                                 training=self.__training)
            conv = separable_conv('conv9', input_data=conv, input_c=256, output_c=512, training=self.__training)
            conv = convolutional('conv10', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training)
            conv = separable_conv('conv11', input_data=conv, input_c=256, output_c=512, training=self.__training)
            conv = convolutional('conv12', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training)

            # ----------**********---------- Detection branch of middle object ----------**********----------
            conv_mbbox = separable_conv(name='conv13', input_data=conv, input_c=256, output_c=512,
                                        training=self.__training)
            conv_mbbox = convolutional(name='conv14', input_data=conv_mbbox,
                                       filters_shape=(1, 1, 512, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_mbbox = decode_nms(name='pred_mbbox', conv_output=conv_mbbox,
                                num_classes=self.__num_classes, stride=self.__strides[1],shape=inputsize//16,gt_pergrid=gt_per_grid,originW=originW,originH=originH,inputsize=inputsize)
            # ----------**********---------- Detection branch of middle object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv15', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)
            conv = upsample_decode(name='upsample1', input_data=conv,shape1=inputsize//16,shape2=inputsize//16)
            conv = route(name='route1', previous_output=feature_map_s, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional(name='conv16', input_data=conv, filters_shape=(1, 1, 32 + 128, 128),
                                 training=self.__training)
            conv = separable_conv(name='conv17', input_data=conv, input_c=128, output_c=256, training=self.__training)
            conv = convolutional(name='conv18', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)
            conv = separable_conv(name='conv19', input_data=conv, input_c=128, output_c=256, training=self.__training)
            conv = convolutional(name='conv20', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training)

            # ----------**********---------- Detection branch of small object ----------**********----------
            conv_sbbox = separable_conv(name='conv21', input_data=conv, input_c=128, output_c=256,
                                        training=self.__training)
            conv_sbbox = convolutional(name='conv22', input_data=conv_sbbox,
                                       filters_shape=(1, 1, 256, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False)
            pred_sbbox = decode_nms(name='pred_sbbox', conv_output=conv_sbbox,
                                num_classes=self.__num_classes, stride=self.__strides[0],shape=inputsize//8,gt_pergrid=gt_per_grid,originW=originW,originH=originH,inputsize=inputsize)
            # ----------**********---------- Detection branch of small object ----------**********----------

            #poseprocessing
            pred_sbbox = tf.reshape(pred_sbbox, (-1, 5+self.__num_classes))
            pred_mbbox = tf.reshape(pred_mbbox, (-1, 5+self.__num_classes))
            pred_lbbox = tf.reshape(pred_lbbox, (-1, 5+self.__num_classes))
            pred_bbox = tf.concat([pred_sbbox, pred_mbbox, pred_lbbox], 0)
            yxyx,conf=tf.split(pred_bbox,[4,1],axis=1)
            conf=tf.squeeze(conf,squeeze_dims=1)
            mask = tf.greater_equal(conf, tf.constant(thres))
            filterboxes = tf.boolean_mask(yxyx, mask)
            filterscores = tf.boolean_mask(conf, mask)

            nms_idx = tf.image.non_max_suppression(boxes=filterboxes,scores=filterscores,max_output_size=100,iou_threshold=iouthres)
            nmsboxes=tf.gather(filterboxes,nms_idx)
            nmsscores = tf.gather(filterscores, nms_idx)
            nmsscores=tf.expand_dims(nmsscores,axis=1)
            ymin,xmin,ymax,xmax=tf.split(nmsboxes,[1,1,1,1],1)
            nmsboxes=tf.concat([xmin,ymin,xmax,ymax],1)

            pred_bbox = tf.concat([nmsboxes,nmsscores],1,name='output/boxconcat')
        for var in tf.global_variables(net_name):
            tf.add_to_collection(net_name, var)
        return pred_bbox

    def build_network_dynamic(self, input_data,statedict, originH,originW,val_reuse=False,inputsize=544,thres=0.1,gt_per_grid=3,kr=False,MNN=False):
        net_name = 'YoloV3'
        with tf.variable_scope(net_name, reuse=val_reuse):
            feature_map_s, feature_map_m, feature_map_l = MobilenetV2_dynamic(input_data, self.__training,statedict)

            conv = convolutional(name='conv0', input_data=feature_map_l, filters_shape=(1, 1, 1280, 512),
                                 training=self.__training,statedict=statedict[19])
            conv = separable_conv(name='conv1', input_data=conv, input_c=512, output_c=1024, training=self.__training,statedict=statedict[20])
            conv = convolutional(name='conv2', input_data=conv, filters_shape=(1, 1, 1024, 512),
                                 training=self.__training,statedict=statedict[21])
            conv = separable_conv(name='conv3', input_data=conv, input_c=512, output_c=1024, training=self.__training,statedict=statedict[22])
            conv = convolutional(name='conv4', input_data=conv, filters_shape=(1, 1, 1024, 512),
                                 training=self.__training,statedict=statedict[23])

            # ----------**********---------- Detection branch of large object ----------**********----------
            conv_lbbox = separable_conv(name='conv5', input_data=conv, input_c=512, output_c=1024,
                                        training=self.__training,statedict=statedict[24])
            conv_lbbox = convolutional(name='conv6', input_data=conv_lbbox,
                                       filters_shape=(1, 1, 1024, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False,statedict=statedict[25])
            if MNN:
                pred_lbbox = decode_validate(name='pred_lbbox', conv_output=conv_lbbox,
                                        num_classes=self.__num_classes, stride=self.__strides[2], shape=inputsize // 32,
                                        gt_pergrid=gt_per_grid)
            else:
                pred_lbbox = decode_nms(name='pred_lbbox', conv_output=conv_lbbox,
                                num_classes=self.__num_classes, stride=self.__strides[2],shape=inputsize//32,gt_pergrid=gt_per_grid,originW=originW,originH=originH,inputsize=inputsize,kr=False)
            # ----------**********---------- Detection branch of large object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv7', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training,statedict=statedict[26])
            conv = upsample_decode(name='upsample0', input_data=conv,shape1=inputsize//32,shape2=inputsize//32)
            conv = route(name='route0', previous_output=feature_map_m, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional('conv8', input_data=conv, filters_shape=(1, 1, 96 + 256, 256),
                                 training=self.__training,statedict=statedict[27])
            conv = separable_conv('conv9', input_data=conv, input_c=256, output_c=512, training=self.__training,statedict=statedict[28])
            conv = convolutional('conv10', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training,statedict=statedict[29])
            conv = separable_conv('conv11', input_data=conv, input_c=256, output_c=512, training=self.__training,statedict=statedict[30])
            conv = convolutional('conv12', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training,statedict=statedict[31])

            # ----------**********---------- Detection branch of middle object ----------**********----------
            conv_mbbox = separable_conv(name='conv13', input_data=conv, input_c=256, output_c=512,
                                        training=self.__training,statedict=statedict[32])
            conv_mbbox = convolutional(name='conv14', input_data=conv_mbbox,
                                       filters_shape=(1, 1, 512, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False,statedict=statedict[33])
            if MNN:
                pred_mbbox = decode_validate(name='pred_mbbox', conv_output=conv_mbbox,
                                        num_classes=self.__num_classes, stride=self.__strides[1], shape=inputsize // 16,
                                        gt_pergrid=gt_per_grid)
            else:
                pred_mbbox = decode_nms(name='pred_mbbox', conv_output=conv_mbbox,
                                num_classes=self.__num_classes, stride=self.__strides[1],shape=inputsize//16,gt_pergrid=gt_per_grid,originW=originW,originH=originH,inputsize=inputsize,kr=False)
            # ----------**********---------- Detection branch of middle object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv15', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training,statedict=statedict[34])
            conv = upsample_decode(name='upsample1', input_data=conv,shape1=inputsize//16,shape2=inputsize//16)
            conv = route(name='route1', previous_output=feature_map_s, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional(name='conv16', input_data=conv, filters_shape=(1, 1, 32 + 128, 128),
                                 training=self.__training,statedict=statedict[35])
            conv = separable_conv(name='conv17', input_data=conv, input_c=128, output_c=256, training=self.__training,statedict=statedict[36])
            conv = convolutional(name='conv18', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training,statedict=statedict[37])
            conv = separable_conv(name='conv19', input_data=conv, input_c=128, output_c=256, training=self.__training,statedict=statedict[38])
            conv = convolutional(name='conv20', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training,statedict=statedict[39])

            # ----------**********---------- Detection branch of small object ----------**********----------
            conv_sbbox = separable_conv(name='conv21', input_data=conv, input_c=128, output_c=256,
                                        training=self.__training,statedict=statedict[40])
            conv_sbbox = convolutional(name='conv22', input_data=conv_sbbox,
                                       filters_shape=(1, 1, 256, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False,statedict=statedict[41])
            if MNN:
                pred_sbbox = decode_validate(name='pred_sbbox', conv_output=conv_sbbox,
                                        num_classes=self.__num_classes, stride=self.__strides[0], shape=inputsize // 8,
                                        gt_pergrid=gt_per_grid)
            else:
                pred_sbbox = decode_nms(name='pred_sbbox', conv_output=conv_sbbox,
                                num_classes=self.__num_classes, stride=self.__strides[0],shape=inputsize//8,gt_pergrid=gt_per_grid,originW=originW,originH=originH,inputsize=inputsize,kr=False)
            # ----------**********---------- Detection branch of small object ----------**********----------
            if MNN:
                pred_sbbox = tf.reshape(pred_sbbox, (-1, 5 + self.__num_classes))
                pred_mbbox = tf.reshape(pred_mbbox, (-1, 5 + self.__num_classes))
                pred_lbbox = tf.reshape(pred_lbbox, (-1, 5 + self.__num_classes))
                pred_bbox = tf.concat([pred_sbbox, pred_mbbox, pred_lbbox], 0, name='output/boxconcat')
            else:
                #poseprocessing
                pred_sbbox = tf.reshape(pred_sbbox, (-1, 5+self.__num_classes))
                pred_mbbox = tf.reshape(pred_mbbox, (-1, 5+self.__num_classes))
                pred_lbbox = tf.reshape(pred_lbbox, (-1, 5+self.__num_classes))
                pred_bbox = tf.concat([pred_sbbox, pred_mbbox, pred_lbbox], 0)
                yxyx,conf=tf.split(pred_bbox,[4,1],axis=1)
                conf=tf.squeeze(conf,squeeze_dims=1)
                mask = tf.greater_equal(conf, tf.constant(thres))
                filterboxes = tf.boolean_mask(yxyx, mask)
                filterscores = tf.boolean_mask(conf, mask)
                nms_idx = tf.image.non_max_suppression(boxes=filterboxes,scores=filterscores,max_output_size=100,iou_threshold=0.5)
                nmsboxes=tf.gather(filterboxes,nms_idx)
                nmsscores = tf.gather(filterscores, nms_idx)
                nmsscores=tf.expand_dims(nmsscores,axis=1)
                ymin,xmin,ymax,xmax=tf.split(nmsboxes,[1,1,1,1],1)
                nmsboxes=tf.concat([xmin,ymin,xmax,ymax],1)

                pred_bbox = tf.concat([nmsboxes,nmsscores],1,name='output/boxconcat')
        for var in tf.global_variables(net_name):
            tf.add_to_collection(net_name, var)
        return pred_bbox
    def build_network_dynamichalf(self, input_data,statedict, originH,originW,val_reuse=False,inputsize=544,thres=0.1,gt_per_grid=2,kr=False,MNN=False):
        net_name = 'YoloV3'
        with tf.variable_scope(net_name, reuse=val_reuse):
            feature_map_s, feature_map_m, feature_map_l = MobilenetV2_dynamic(input_data, self.__training,statedict)

            conv = convolutional(name='conv0', input_data=feature_map_l, filters_shape=(1, 1, 1280, 512),
                                 training=self.__training,statedict=statedict[19])
            conv = separable_conv(name='conv1', input_data=conv, input_c=512, output_c=1024, training=self.__training,statedict=statedict[20])
            conv = separable_conv(name='conv2', input_data=conv,input_c=1024, output_c=512,
                                 training=self.__training,statedict=statedict[21])
            conv = separable_conv(name='conv3', input_data=conv, input_c=512, output_c=1024, training=self.__training,statedict=statedict[22])
            conv = separable_conv(name='conv4', input_data=conv, input_c=1024, output_c=512,
                                 training=self.__training,statedict=statedict[23])

            # ----------**********---------- Detection branch of large object ----------**********----------
            conv_lbbox = separable_conv(name='conv5', input_data=conv, input_c=512, output_c=1024,
                                        training=self.__training,statedict=statedict[24])
            conv_lbbox = convolutional(name='conv6', input_data=conv_lbbox,
                                       filters_shape=(1, 1, 1024, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False,statedict=statedict[25])
            if MNN:
                pred_lbbox = decode_validate(name='pred_lbbox', conv_output=conv_lbbox,
                                        num_classes=self.__num_classes, stride=self.__strides[2], shape=inputsize // 32,
                                        gt_pergrid=gt_per_grid)
            else:
                pred_lbbox = decode_nms(name='pred_lbbox', conv_output=conv_lbbox,
                                num_classes=self.__num_classes, stride=self.__strides[2],shape=inputsize//32,gt_pergrid=gt_per_grid,originW=originW,originH=originH,inputsize=inputsize,kr=False)
            # ----------**********---------- Detection branch of large object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv7', input_data=conv, filters_shape=(1, 1, 512, 256),
                                 training=self.__training,statedict=statedict[26])
            conv = upsample_decode(name='upsample0', input_data=conv,shape1=inputsize//32,shape2=inputsize//32)
            conv = route(name='route0', previous_output=feature_map_m, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional('conv8', input_data=conv, filters_shape=(1, 1, 96 + 256, 256),
                                 training=self.__training,statedict=statedict[27])
            conv = separable_conv('conv9', input_data=conv, input_c=256, output_c=512, training=self.__training,statedict=statedict[28])
            conv = separable_conv('conv10', input_data=conv, input_c=512, output_c=256,
                                 training=self.__training,statedict=statedict[29])
            conv = separable_conv('conv11', input_data=conv, input_c=256, output_c=512, training=self.__training,statedict=statedict[30])
            conv = separable_conv('conv12', input_data=conv, input_c=512, output_c=256,
                                 training=self.__training,statedict=statedict[31])

            # ----------**********---------- Detection branch of middle object ----------**********----------
            conv_mbbox = separable_conv(name='conv13', input_data=conv, input_c=256, output_c=512,
                                        training=self.__training,statedict=statedict[32])
            conv_mbbox = convolutional(name='conv14', input_data=conv_mbbox,
                                       filters_shape=(1, 1, 512, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False,statedict=statedict[33])
            if MNN:
                pred_mbbox = decode_validate(name='pred_mbbox', conv_output=conv_mbbox,
                                        num_classes=self.__num_classes, stride=self.__strides[1], shape=inputsize // 16,
                                        gt_pergrid=gt_per_grid)
            else:
                pred_mbbox = decode_nms(name='pred_mbbox', conv_output=conv_mbbox,
                                num_classes=self.__num_classes, stride=self.__strides[1],shape=inputsize//16,gt_pergrid=gt_per_grid,originW=originW,originH=originH,inputsize=inputsize,kr=False)
            # ----------**********---------- Detection branch of middle object ----------**********----------

            # ----------**********---------- up sample and merge features map ----------**********----------
            conv = convolutional(name='conv15', input_data=conv, filters_shape=(1, 1, 256, 128),
                                 training=self.__training,statedict=statedict[34])
            conv = upsample_decode(name='upsample1', input_data=conv,shape1=inputsize//16,shape2=inputsize//16)
            conv = route(name='route1', previous_output=feature_map_s, current_output=conv)
            # ----------**********---------- up sample and merge features map ----------**********----------

            conv = convolutional(name='conv16', input_data=conv, filters_shape=(1, 1, 32 + 128, 128),
                                 training=self.__training,statedict=statedict[35])
            conv = separable_conv(name='conv17', input_data=conv, input_c=128, output_c=256, training=self.__training,statedict=statedict[36])
            conv = separable_conv(name='conv18', input_data=conv, input_c=256, output_c=128,
                                 training=self.__training,statedict=statedict[37])
            conv = separable_conv(name='conv19', input_data=conv, input_c=128, output_c=256, training=self.__training,statedict=statedict[38])
            conv = separable_conv(name='conv20', input_data=conv,input_c=256, output_c=128,
                                 training=self.__training,statedict=statedict[39])

            # ----------**********---------- Detection branch of small object ----------**********----------
            conv_sbbox = separable_conv(name='conv21', input_data=conv, input_c=128, output_c=256,
                                        training=self.__training,statedict=statedict[40])
            conv_sbbox = convolutional(name='conv22', input_data=conv_sbbox,
                                       filters_shape=(1, 1, 256, gt_per_grid * (self.__num_classes + 5)),
                                       training=self.__training, downsample=False, activate=False, bn=False,statedict=statedict[41])
            if MNN:
                pred_sbbox = decode_validate(name='pred_sbbox', conv_output=conv_sbbox,
                                        num_classes=self.__num_classes, stride=self.__strides[0], shape=inputsize // 8,
                                        gt_pergrid=gt_per_grid)
            else:
                pred_sbbox = decode_nms(name='pred_sbbox', conv_output=conv_sbbox,
                                num_classes=self.__num_classes, stride=self.__strides[0],shape=inputsize//8,gt_pergrid=gt_per_grid,originW=originW,originH=originH,inputsize=inputsize,kr=False)
            # ----------**********---------- Detection branch of small object ----------**********----------
            if MNN:
                pred_sbbox = tf.reshape(pred_sbbox, (-1, 5 + self.__num_classes))
                pred_mbbox = tf.reshape(pred_mbbox, (-1, 5 + self.__num_classes))
                pred_lbbox = tf.reshape(pred_lbbox, (-1, 5 + self.__num_classes))
                pred_bbox = tf.concat([pred_sbbox, pred_mbbox, pred_lbbox], 0, name='output/boxconcat')
            else:
                #poseprocessing
                pred_sbbox = tf.reshape(pred_sbbox, (-1, 5+self.__num_classes))
                pred_mbbox = tf.reshape(pred_mbbox, (-1, 5+self.__num_classes))
                pred_lbbox = tf.reshape(pred_lbbox, (-1, 5+self.__num_classes))
                pred_bbox = tf.concat([pred_sbbox, pred_mbbox, pred_lbbox], 0)
                yxyx,conf=tf.split(pred_bbox,[4,1],axis=1)
                conf=tf.squeeze(conf,squeeze_dims=1)
                mask = tf.greater_equal(conf, tf.constant(thres))
                filterboxes = tf.boolean_mask(yxyx, mask)
                filterscores = tf.boolean_mask(conf, mask)
                nms_idx = tf.image.non_max_suppression(boxes=filterboxes,scores=filterscores,max_output_size=100,iou_threshold=0.5)
                nmsboxes=tf.gather(filterboxes,nms_idx)
                nmsscores = tf.gather(filterscores, nms_idx)
                nmsscores=tf.expand_dims(nmsscores,axis=1)
                ymin,xmin,ymax,xmax=tf.split(nmsboxes,[1,1,1,1],1)
                nmsboxes=tf.concat([xmin,ymin,xmax,ymax],1)

                pred_bbox = tf.concat([nmsboxes,nmsscores],1,name='output/boxconcat')
        for var in tf.global_variables(net_name):
            tf.add_to_collection(net_name, var)
        return pred_bbox

    def __focal(self, target, actual, alpha=1, gamma=2):
        focal = alpha * tf.pow(tf.abs(target - actual), gamma)
        return focal

    def __loss_per_scale(self, name, conv, pred, label, bboxes, stride,gt_per_grid=2):
        """
        :param name: loss的名字
        :param conv: conv是yolo卷积层的原始输出
        shape为(batch_size, output_size, output_size, anchor_per_scale * (5 + num_class))
        :param pred: conv是yolo输出的预测bbox的信息(x, y, w, h, conf, prob)，
        其中(x, y, w, h)的大小是相对于input_size的，如input_size=416，(x, y, w, h) = (120, 200, 50, 70)
        shape为(batch_size, output_size, output_size, anchor_per_scale, 5 + num_class)
        :param label: shape为(batch_size, output_size, output_size, anchor_per_scale, 6 + num_classes)
        只有负责预测GT的对应位置的数据才为(xmin, ymin, xmax, ymax, 1, classes, mixup_weights),
        其他位置的数据都为(0, 0, 0, 0, 0, 0..., 1)
        :param bboxes: shape为(batch_size, max_bbox_per_scale, 4)，
        存储的坐标为(xmin, ymin, xmax, ymax)
        bboxes用于计算相应detector的预测框与该detector负责预测的所有bbox的IOU
        :param anchors: 相应detector的anchors
        :param stride: 相应detector的stride
        """
        with tf.name_scope(name):
            conv_shape = tf.shape(conv)
            batch_size = conv_shape[0]
            output_size = conv_shape[1]
            input_size = stride * output_size
            conv = tf.reshape(conv, (batch_size, output_size, output_size,
                                     gt_per_grid, 5 + self.__num_classes))
            conv_raw_conf = conv[..., 4:5]
            # conv_raw_prob = conv[..., 5:]

            pred_coor = pred[..., 0:4]
            pred_conf = pred[..., 4:5]

            label_coor = label[..., 0:4]
            respond_bbox = label[..., 4:5]
            label_prob = label[..., 5:-1]
            label_mixw = label[..., -1:]

            # 计算GIOU损失
            GIOU = tools.GIOU(pred_coor, label_coor)
            GIOU = GIOU[..., np.newaxis]
            input_size = tf.cast(input_size, tf.float32)
            bbox_wh = label_coor[..., 2:] - label_coor[..., :2]
            bbox_loss_scale = 2.0 - 1.0 * bbox_wh[..., 0:1] * bbox_wh[..., 1:2] / (input_size ** 2)
            GIOU_loss = respond_bbox * bbox_loss_scale * (1.0 - GIOU)

            # (2)计算confidence损失
            iou = tools.iou_calc3(pred_coor[:, :, :, :, np.newaxis, :],
                                  bboxes[:, np.newaxis, np.newaxis, np.newaxis, :, : ])
            max_iou = tf.reduce_max(iou, axis=-1)
            max_iou = max_iou[..., np.newaxis]
            respond_bgd = (1.0 - respond_bbox) * tf.cast(max_iou < self.__iou_loss_thresh, tf.float32)

            conf_focal = self.__focal(respond_bbox, pred_conf)

            conf_loss = conf_focal * (
                    respond_bbox * tf.nn.sigmoid_cross_entropy_with_logits(labels=respond_bbox, logits=conv_raw_conf)
                    +
                    respond_bgd * tf.nn.sigmoid_cross_entropy_with_logits(labels=respond_bbox, logits=conv_raw_conf)
            )

            # (3)计算classes损失
            # prob_loss = respond_bbox * tf.nn.sigmoid_cross_entropy_with_logits(labels=label_prob, logits=conv_raw_prob)
            # loss = tf.concat([GIOU_loss, conf_loss, prob_loss], axis=-1)
            loss = tf.concat([GIOU_loss, conf_loss], axis=-1)
            loss = loss * label_mixw
            loss = tf.reduce_mean(tf.reduce_sum(loss, axis=[1, 2, 3, 4]))
            return loss

    def loss(self,
             conv_sbbox, conv_mbbox, conv_lbbox,
             pred_sbbox, pred_mbbox, pred_lbbox,
             label_sbbox, label_mbbox, label_lbbox,
             sbboxes, mbboxes, lbboxes):
        """
        :param conv_sbbox: shape为(batch_size, image_size / 8, image_size / 8, anchors_per_scale * (5 + num_classes))
        :param conv_mbbox: shape为(batch_size, image_size / 16, image_size / 16, anchors_per_scale * (5 + num_classes))
        :param conv_lbbox: shape为(batch_size, image_size / 32, image_size / 32, anchors_per_scale * (5 + num_classes))
        :param pred_sbbox: shape为(batch_size, image_size / 8, image_size / 8, anchors_per_scale, (5 + num_classes))
        :param pred_mbbox: shape为(batch_size, image_size / 16, image_size / 16, anchors_per_scale, (5 + num_classes))
        :param pred_lbbox: shape为(batch_size, image_size / 32, image_size / 32, anchors_per_scale, (5 + num_classes))
        :param label_sbbox: shape为(batch_size, input_size / 8, input_size / 8, anchor_per_scale, 6 + num_classes)
        :param label_mbbox: shape为(batch_size, input_size / 16, input_size / 16, anchor_per_scale, 6 + num_classes)
        :param label_lbbox: shape为(batch_size, input_size / 32, input_size / 32, anchor_per_scale, 6 + num_classes)
        :param sbboxes: shape为(batch_size, max_bbox_per_scale, 4)
        :param mbboxes: shape为(batch_size, max_bbox_per_scale, 4)
        :param lbboxes: shape为(batch_size, max_bbox_per_scale, 4)
        :return:
        """
        loss_sbbox = self.__loss_per_scale('loss_sbbox', conv_sbbox, pred_sbbox, label_sbbox, sbboxes,
                                           self.__strides[0])
        loss_mbbox = self.__loss_per_scale('loss_mbbox', conv_mbbox, pred_mbbox, label_mbbox, mbboxes,
                                           self.__strides[1])
        loss_lbbox = self.__loss_per_scale('loss_lbbox', conv_lbbox, pred_lbbox, label_lbbox, lbboxes,
                                           self.__strides[2])
        with tf.name_scope('loss'):
            loss = loss_sbbox + loss_mbbox + loss_lbbox
        return loss