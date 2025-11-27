#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
68 Keypoints Annotation Tool
A GUI tool for annotating 68 facial landmarks on images
"""

import sys
import os
import json
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QListWidget, QListWidgetItem, QLabel,
                             QMenuBar, QMenu, QAction, QFileDialog, QMessageBox,
                             QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
                             QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem,
                             QGraphicsItemGroup, QDockWidget, QToolBar, QCheckBox, QSplitter)
from PyQt5.QtCore import Qt, QPointF, pyqtSignal
from PyQt5.QtGui import (QPixmap, QPen, QBrush, QColor, QPainter, QImage,
                         QKeySequence, QTransform, QCursor, QFont, QIcon)


def get_resource_path(relative_path):
    """获取资源文件的绝对路径，兼容开发环境和PyInstaller打包后的环境"""
    try:
        # PyInstaller创建临时文件夹,将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except AttributeError:
        # 开发环境中使用当前文件所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class KeypointGraphicsItem(QGraphicsEllipseItem):
    """自定义关键点图形项"""
    def __init__(self, x, y, radius, keypoint_id, parent=None):
        super().__init__(-radius, -radius, radius*2, radius*2, parent)
        self.keypoint_id = keypoint_id
        self.setPos(x, y)
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges, True)
        self.setCursor(QCursor(Qt.PointingHandCursor))

        # 默认样式
        self.normal_pen = QPen(QColor(0, 255, 0), 2)
        self.selected_pen = QPen(QColor(255, 0, 0), 3)
        self.setPen(self.normal_pen)
        self.setBrush(QBrush(QColor(0, 255, 0, 100)))

        # 🔍 记录拖动状态
        self.is_being_dragged = False
        self.drag_start_pos = None

    def itemChange(self, change, value):
        """监听图形项的变化"""
        if change == QGraphicsEllipseItem.ItemPositionChange:
            # 位置正在改变
            if not self.is_being_dragged:
                # 第一次位置改变，记录开始拖动
                self.is_being_dragged = True
                self.drag_start_pos = self.pos()
                print(f"[DEBUG] 关键点 {self.keypoint_id} 开始拖动: start_pos={self.drag_start_pos}")
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        """鼠标释放 - 拖动结束"""
        if self.is_being_dragged:
            final_pos = self.pos()
            print(f"[DEBUG] KeypointGraphicsItem {self.keypoint_id} 拖动结束: final_pos={final_pos}")

            # 计算移动距离
            if self.drag_start_pos is not None:
                dx = abs(final_pos.x() - self.drag_start_pos.x())
                dy = abs(final_pos.y() - self.drag_start_pos.y())
                print(f"[DEBUG] 关键点 {self.keypoint_id} 移动距离: dx={dx:.2f}, dy={dy:.2f}")

                # 如果真的移动了（超过1像素），通知ImageView
                if dx > 1.0 or dy > 1.0:
                    # 获取父视图并发射信号
                    view = self.scene().views()[0] if self.scene() and self.scene().views() else None
                    if view and hasattr(view, 'keypoint_moved'):
                        print(f"[DEBUG] 图形项直接触发 keypoint_moved 信号: ID={self.keypoint_id}")
                        view.keypoint_moved.emit(self.keypoint_id, final_pos.x(), final_pos.y())
                else:
                    print(f"[DEBUG] 移动距离太小，不触发信号")

            self.is_being_dragged = False
            self.drag_start_pos = None
        super().mouseReleaseEvent(event)

    def paint(self, painter, option, widget):
        """自定义绘制"""
        if self.isSelected():
            self.setPen(self.selected_pen)
            self.setBrush(QBrush(QColor(255, 0, 0, 150)))
        else:
            self.setPen(self.normal_pen)
            self.setBrush(QBrush(QColor(0, 255, 0, 100)))
        super().paint(painter, option, widget)


class KeypointCrossItem(QGraphicsItemGroup):
    """十字标记关键点"""
    def __init__(self, x, y, size, keypoint_id, parent=None):
        super().__init__(parent)
        self.keypoint_id = keypoint_id
        self.size = size
        self.setPos(x, y)
        self.setFlag(QGraphicsItemGroup.ItemIsMovable, True)
        self.setFlag(QGraphicsItemGroup.ItemIsSelectable, True)
        self.setFlag(QGraphicsItemGroup.ItemSendsGeometryChanges, True)
        self.setCursor(QCursor(Qt.PointingHandCursor))

        # 创建十字
        pen = QPen(QColor(0, 255, 0), 2)
        self.line1 = QGraphicsLineItem(-size, 0, size, 0, self)
        self.line2 = QGraphicsLineItem(0, -size, 0, size, self)
        self.line1.setPen(pen)
        self.line2.setPen(pen)

        self.addToGroup(self.line1)
        self.addToGroup(self.line2)

        # 🔍 记录拖动状态
        self.is_being_dragged = False
        self.drag_start_pos = None

    def itemChange(self, change, value):
        """监听图形项的变化"""
        if change == QGraphicsItemGroup.ItemPositionChange:
            # 位置正在改变
            if not self.is_being_dragged:
                # 第一次位置改变，记录开始拖动
                self.is_being_dragged = True
                self.drag_start_pos = self.pos()
                print(f"[DEBUG] 关键点 {self.keypoint_id} 开始拖动: start_pos={self.drag_start_pos}")
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        """鼠标释放 - 拖动结束"""
        if self.is_being_dragged:
            final_pos = self.pos()
            print(f"[DEBUG] KeypointCrossItem {self.keypoint_id} 拖动结束: final_pos={final_pos}")

            # 计算移动距离
            if self.drag_start_pos is not None:
                dx = abs(final_pos.x() - self.drag_start_pos.x())
                dy = abs(final_pos.y() - self.drag_start_pos.y())
                print(f"[DEBUG] 关键点 {self.keypoint_id} 移动距离: dx={dx:.2f}, dy={dy:.2f}")

                # 如果真的移动了（超过1像素），通知ImageView
                if dx > 1.0 or dy > 1.0:
                    # 获取父视图并发射信号
                    view = self.scene().views()[0] if self.scene() and self.scene().views() else None
                    if view and hasattr(view, 'keypoint_moved'):
                        print(f"[DEBUG] 图形项直接触发 keypoint_moved 信号: ID={self.keypoint_id}")
                        view.keypoint_moved.emit(self.keypoint_id, final_pos.x(), final_pos.y())
                else:
                    print(f"[DEBUG] 移动距离太小，不触发信号")

            self.is_being_dragged = False
            self.drag_start_pos = None
        super().mouseReleaseEvent(event)

    def set_selected_style(self, selected):
        """设置选中样式"""
        if selected:
            pen = QPen(QColor(255, 0, 0), 3)
        else:
            pen = QPen(QColor(0, 255, 0), 2)
        self.line1.setPen(pen)
        self.line2.setPen(pen)


class ImageView(QGraphicsView):
    """图片显示视图，支持缩放和拖动"""
    keypoint_added = pyqtSignal(int, float, float)  # id, x, y
    keypoint_moved = pyqtSignal(int, float, float)  # id, x, y
    keypoint_selected = pyqtSignal(int)  # id

    def __init__(self, parent=None, auto_fit=False):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # 视图设置
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        # 图片和关键点
        self.pixmap_item = None
        self.keypoints = {}  # {id: QGraphicsItem}
        self.current_image_path = None

        # 交互状态
        self.is_panning = False
        self.pan_start_pos = None
        self.adding_keypoint_id = None  # 正在添加的关键点ID
        self.keypoint_press_pos = None  # 记录关键点按下时的位置，用于检测是否真的移动了
        self.pressed_keypoint_id = None  # 记录被按下的关键点ID

        # 显示设置
        self.show_as_circle = True  # True=圆点, False=十字
        self.show_labels = False  # 是否显示编号
        self.label_items = {}  # {id: QGraphicsTextItem}

        # 缩放范围
        self.min_scale = 0.1
        self.max_scale = 10.0
        self.current_scale = 1.0

        # 是否自动适应窗口（用于参考图）
        self.auto_fit = auto_fit

    def load_image(self, image_path):
        """加载图片"""
        self.scene.clear()
        self.keypoints.clear()
        self.label_items.clear()
        self.current_image_path = image_path

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            return False

        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        self.scene.setSceneRect(self.pixmap_item.boundingRect())

        # 适应窗口
        self.fit_in_view()
        return True

    def fit_in_view(self):
        """适应窗口大小"""
        if self.pixmap_item:
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
            self.current_scale = self.transform().m11()

    def get_image_size(self):
        """获取图片尺寸"""
        if self.pixmap_item:
            rect = self.pixmap_item.boundingRect()
            return rect.width(), rect.height()
        return None, None

    def add_keypoint(self, keypoint_id, x, y):
        """添加关键点"""
        if keypoint_id in self.keypoints:
            # 更新位置
            self.keypoints[keypoint_id].setPos(x, y)
            # 同时更新标签位置
            if keypoint_id in self.label_items:
                self.label_items[keypoint_id].setPos(x + 1.5, y - 1.5)
        else:
            # 创建新的关键点
            if self.show_as_circle:
                item = KeypointGraphicsItem(x, y, 3, keypoint_id)  # 半径3px方便查看
            else:
                item = KeypointCrossItem(x, y, 6, keypoint_id)  # 大小6px方便查看

            # 设置初始缩放，使其大小不受视图缩放影响
            self.update_keypoint_scale(item)

            self.scene.addItem(item)
            self.keypoints[keypoint_id] = item

            # 添加标签
            if self.show_labels:
                self.add_label(keypoint_id, x, y)

    def update_keypoint_scale(self, item):
        """更新关键点缩放，使其在不同缩放级别保持合适的大小"""
        # 使用逆向缩放，使关键点在视觉上保持恒定大小
        scale_factor = 1.0 / self.current_scale
        item.setScale(scale_factor)

    def update_all_keypoints_scale(self):
        """更新所有关键点的缩放"""
        for item in self.keypoints.values():
            self.update_keypoint_scale(item)

        # 同时更新标签
        for label in self.label_items.values():
            scale_factor = 1.0 / self.current_scale
            label.setScale(scale_factor)

    def add_label(self, keypoint_id, x, y):
        """添加关键点编号标签"""
        if keypoint_id in self.label_items:
            # 标签位置紧贴点，偏移量为1.5像素
            self.label_items[keypoint_id].setPos(x + 1.5, y - 1.5)
        else:
            label = QGraphicsTextItem(str(keypoint_id))
            # 标签位置紧贴点，偏移量为1.5像素
            label.setPos(x + 1.5, y - 1.5)
            label.setDefaultTextColor(QColor(255, 255, 0))
            font = QFont()
            # 字体大小设为10点
            font.setPointSize(10)
            font.setBold(False)
            label.setFont(font)

            # 设置初始缩放，使其大小不受视图缩放影响
            scale_factor = 1.0 / self.current_scale
            label.setScale(scale_factor)

            self.scene.addItem(label)
            self.label_items[keypoint_id] = label

    def remove_keypoint(self, keypoint_id):
        """删除关键点"""
        if keypoint_id in self.keypoints:
            self.scene.removeItem(self.keypoints[keypoint_id])
            del self.keypoints[keypoint_id]

        if keypoint_id in self.label_items:
            self.scene.removeItem(self.label_items[keypoint_id])
            del self.label_items[keypoint_id]

    def clear_keypoints(self):
        """清除所有关键点"""
        for item in list(self.keypoints.values()):
            self.scene.removeItem(item)
        self.keypoints.clear()

        for item in list(self.label_items.values()):
            self.scene.removeItem(item)
        self.label_items.clear()

    def get_keypoint_position(self, keypoint_id):
        """获取关键点位置"""
        if keypoint_id in self.keypoints:
            pos = self.keypoints[keypoint_id].pos()
            return pos.x(), pos.y()
        return None

    def select_keypoint(self, keypoint_id):
        """选中关键点"""
        # 清除其他选择
        for kp_id, item in self.keypoints.items():
            if hasattr(item, 'setSelected'):
                item.setSelected(kp_id == keypoint_id)
            elif isinstance(item, KeypointCrossItem):
                item.set_selected_style(kp_id == keypoint_id)

    def set_adding_mode(self, keypoint_id):
        """设置添加关键点模式"""
        self.adding_keypoint_id = keypoint_id
        if keypoint_id is not None:
            self.setCursor(QCursor(Qt.CrossCursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))

    def toggle_display_style(self, show_circle):
        """切换显示样式"""
        self.show_as_circle = show_circle
        # 重新创建所有关键点
        old_keypoints = {}
        for kp_id, item in self.keypoints.items():
            pos = item.pos()
            old_keypoints[kp_id] = (pos.x(), pos.y())
            self.scene.removeItem(item)

        self.keypoints.clear()

        for kp_id, (x, y) in old_keypoints.items():
            self.add_keypoint(kp_id, x, y)

    def toggle_labels(self, show):
        """切换标签显示"""
        self.show_labels = show
        if show:
            for kp_id, item in self.keypoints.items():
                pos = item.pos()
                self.add_label(kp_id, pos.x(), pos.y())
        else:
            for label in self.label_items.values():
                self.scene.removeItem(label)
            self.label_items.clear()

    def wheelEvent(self, event):
        """鼠标滚轮缩放"""
        factor = 1.2
        if event.angleDelta().y() > 0:
            # 放大
            if self.current_scale * factor <= self.max_scale:
                self.scale(factor, factor)
                self.current_scale *= factor
                self.update_all_keypoints_scale()  # 更新关键点大小
        else:
            # 缩小
            if self.current_scale / factor >= self.min_scale:
                self.scale(1/factor, 1/factor)
                self.current_scale /= factor
                self.update_all_keypoints_scale()  # 更新关键点大小

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        scene_pos = self.mapToScene(event.pos())

        # 左键点击
        if event.button() == Qt.LeftButton:
            # 检查是否在添加关键点模式
            if self.adding_keypoint_id is not None:
                # 添加关键点
                self.add_keypoint(self.adding_keypoint_id, scene_pos.x(), scene_pos.y())
                self.keypoint_added.emit(self.adding_keypoint_id, scene_pos.x(), scene_pos.y())
                self.adding_keypoint_id = None
                self.setCursor(QCursor(Qt.ArrowCursor))
            else:
                # 检查是否点击了关键点
                item = self.scene.itemAt(scene_pos, QTransform())
                if isinstance(item, (KeypointGraphicsItem, KeypointCrossItem)):
                    # 选中关键点
                    self.keypoint_selected.emit(item.keypoint_id)
                    # 记录按下时的位置和ID，用于后续判断是否真的移动了
                    self.keypoint_press_pos = item.pos()
                    self.pressed_keypoint_id = item.keypoint_id
                    # 🔍 调试：打印按下事件
                    print(f"[DEBUG] 鼠标按下关键点: ID={item.keypoint_id}, pos={item.pos()}")
                    super().mousePressEvent(event)
                elif item == self.pixmap_item or item is None:
                    # 点击了空白区域，取消选择
                    self.select_keypoint(-1)
                    super().mousePressEvent(event)
                else:
                    super().mousePressEvent(event)

        # 右键拖动图片
        elif event.button() == Qt.RightButton:
            self.is_panning = True
            self.pan_start_pos = event.pos()
            self.setCursor(QCursor(Qt.ClosedHandCursor))

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.is_panning and self.pan_start_pos:
            # 右键拖动图片
            delta = event.pos() - self.pan_start_pos
            self.pan_start_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.RightButton:
            self.is_panning = False
            self.setCursor(QCursor(Qt.ArrowCursor))

        # 检查关键点是否移动（修复快速拖动时鼠标不在关键点上的问题）
        if event.button() == Qt.LeftButton:
            # 🔍 调试：打印释放事件的状态
            print(f"[DEBUG] 鼠标释放: press_pos={self.keypoint_press_pos}, pressed_id={self.pressed_keypoint_id}")

            if self.keypoint_press_pos is not None and self.pressed_keypoint_id is not None:
                # 直接检查被按下的关键点是否移动了
                if self.pressed_keypoint_id in self.keypoints:
                    item = self.keypoints[self.pressed_keypoint_id]
                    pos = item.pos()
                    # 计算移动距离，设置一个阈值(1像素)来避免浮点误差
                    dx = abs(pos.x() - self.keypoint_press_pos.x())
                    dy = abs(pos.y() - self.keypoint_press_pos.y())
                    print(f"[DEBUG] 关键点 {self.pressed_keypoint_id} 移动距离: dx={dx:.2f}, dy={dy:.2f}")

                    if dx > 1.0 or dy > 1.0:  # 移动距离大于1像素才认为是真的移动
                        print(f"[DEBUG] 触发 keypoint_moved 信号: ID={self.pressed_keypoint_id}")
                        self.keypoint_moved.emit(self.pressed_keypoint_id, pos.x(), pos.y())
                        # 更新标签位置
                        if self.pressed_keypoint_id in self.label_items:
                            self.label_items[self.pressed_keypoint_id].setPos(pos.x() + 1.5, pos.y() - 1.5)
                    else:
                        print(f"[DEBUG] 移动距离太小，不触发信号")
                else:
                    print(f"[DEBUG] 警告: pressed_keypoint_id={self.pressed_keypoint_id} 不在 keypoints 字典中")

                # 清除按下位置和ID记录
                self.keypoint_press_pos = None
                self.pressed_keypoint_id = None

        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        """右键菜单"""
        # 这里可以添加右键菜单选项
        pass

    def resizeEvent(self, event):
        """窗口大小变化时的处理"""
        super().resizeEvent(event)
        # 如果是自动适应模式（参考图），在窗口大小变化时重新适应
        if self.auto_fit and self.pixmap_item:
            self.fit_in_view()


class KeypointListWidget(QListWidget):
    """关键点列表控件，支持拖拽重新编号"""
    swap_keypoints = pyqtSignal(int, int)  # 交换两个关键点的编号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setSelectionMode(QListWidget.SingleSelection)

        # 拖拽相关
        self.drag_start_index = None

    def startDrag(self, supportedActions):
        """开始拖拽"""
        item = self.currentItem()
        if item:
            self.drag_start_index = self.row(item)
        super().startDrag(supportedActions)

    def dropEvent(self, event):
        """放置事件"""
        drop_index = self.indexAt(event.pos()).row()

        if self.drag_start_index is not None and drop_index != -1:
            # 获取两个关键点的ID
            start_id = self.drag_start_index + 1
            drop_id = drop_index + 1

            # 询问是否交换
            reply = QMessageBox.question(
                self, '确认交换',
                f'是否要将 {start_id} 号点和 {drop_id} 号点位置互换？',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.swap_keypoints.emit(start_id, drop_id)

        self.drag_start_index = None
        # 不调用super().dropEvent()以防止默认行为


class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("68 Keypoints Annotation Tool")
        self.setGeometry(100, 100, 1400, 900)

        # 数据
        self.current_dir = None
        self.image_files = []
        self.current_image_index = -1
        self.keypoints_data = {}  # {id: (x, y)}
        self.auto_save = True
        self.annotation_format = 'txt'  # 默认使用txt格式，可选 'json' 或 'txt'

        # 标准参考图
        self.reference_image_path = None
        self.reference_keypoints = {}

        # 撤销/重做
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo_steps = 10

        # 创建UI
        self.init_ui()

        # 加载默认标准图
        default_ref_path = get_resource_path("std_pic/facial_landmarks_68markup.jpg")
        if os.path.exists(default_ref_path):
            self.load_reference_image(default_ref_path)

    def init_ui(self):
        """初始化UI"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)

        # 左侧：图片显示区域
        self.image_view = ImageView()
        self.image_view.keypoint_added.connect(self.on_keypoint_added)
        self.image_view.keypoint_moved.connect(self.on_keypoint_moved)
        self.image_view.keypoint_selected.connect(self.on_keypoint_selected)

        # 右侧：分割器（关键点列表 + 标准图）
        right_splitter = QSplitter(Qt.Vertical)

        # 关键点列表
        keypoint_widget = QWidget()
        keypoint_layout = QVBoxLayout(keypoint_widget)
        keypoint_layout.setContentsMargins(5, 5, 5, 5)

        keypoint_label = QLabel("关键点列表")
        keypoint_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        keypoint_layout.addWidget(keypoint_label)

        self.keypoint_list = KeypointListWidget()
        self.keypoint_list.itemClicked.connect(self.on_list_item_clicked)
        self.keypoint_list.swap_keypoints.connect(self.swap_keypoints)
        keypoint_layout.addWidget(self.keypoint_list)

        # 初始化68个关键点
        self.init_keypoint_list()

        right_splitter.addWidget(keypoint_widget)

        # 标准参考图
        self.reference_view = ImageView(auto_fit=True)  # 启用自动适应模式
        self.reference_view.keypoint_selected.connect(self.on_reference_keypoint_selected)
        # 设置参考视图的滚动条策略：始终不显示滚动条，图片会自动缩放到完整显示
        self.reference_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.reference_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        reference_dock_widget = QWidget()
        reference_layout = QVBoxLayout(reference_dock_widget)
        reference_layout.setContentsMargins(5, 5, 5, 5)

        reference_label = QLabel("标准参考图")
        reference_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        reference_layout.addWidget(reference_label)
        reference_layout.addWidget(self.reference_view)

        # 参考视图的大小会在加载图片时根据图片宽高比动态设置

        right_splitter.addWidget(reference_dock_widget)
        # 调整伸缩因子：关键点列表和参考图各占一半，让参考图有更多空间
        right_splitter.setStretchFactor(0, 1)
        right_splitter.setStretchFactor(1, 1)

        # 添加到主布局
        main_layout.addWidget(self.image_view, 3)
        main_layout.addWidget(right_splitter, 1)

        # 状态栏
        self.status_label = QLabel("就绪")
        self.statusBar().addWidget(self.status_label)

        self.progress_label = QLabel("")
        self.statusBar().addPermanentWidget(self.progress_label)

        # 创建菜单和工具栏
        self.create_menus()
        self.create_toolbar()

    def init_keypoint_list(self):
        """初始化关键点列表"""
        self.keypoint_list.clear()
        for i in range(1, 69):
            item = QListWidgetItem(f"{i}: 未标注")
            item.setForeground(QColor(255, 100, 100))  # 未标注显示红色
            self.keypoint_list.addItem(item)

    def pixel_to_ratio(self, x, y):
        """将像素坐标转换为比例系数（0-1）"""
        width, height = self.image_view.get_image_size()
        if width and height and width > 0 and height > 0:
            ratio_x = x / width
            ratio_y = y / height
            return ratio_x, ratio_y
        # 失败时返回None，避免返回错误类型的值导致数据损坏
        print(f"警告: 无法转换像素坐标({x}, {y})为比例，图片尺寸为({width}, {height})")
        return None, None

    def ratio_to_pixel(self, ratio_x, ratio_y):
        """将比例系数转换为像素坐标"""
        width, height = self.image_view.get_image_size()
        if width and height and width > 0 and height > 0:
            x = ratio_x * width
            y = ratio_y * height
            return x, y
        # 失败时返回None，避免返回错误类型的值导致显示错误
        print(f"警告: 无法转换比例({ratio_x}, {ratio_y})为像素，图片尺寸为({width}, {height})")
        return None, None

    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        open_dir_action = QAction("打开目录", self)
        open_dir_action.setShortcut("Ctrl+O")
        open_dir_action.triggered.connect(self.open_directory)
        file_menu.addAction(open_dir_action)

        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_annotations)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        select_ref_action = QAction("选择标准图", self)
        select_ref_action.triggered.connect(self.select_reference_image)
        file_menu.addAction(select_ref_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")

        undo_action = QAction("撤销", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("重做", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        clear_action = QAction("清空标注", self)
        clear_action.setShortcut("Ctrl+R")
        clear_action.triggered.connect(self.clear_annotations)
        edit_menu.addAction(clear_action)

        delete_action = QAction("删除选中点", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self.delete_selected_keypoint)
        edit_menu.addAction(delete_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图")

        fit_view_action = QAction("适应窗口", self)
        fit_view_action.setShortcut("Ctrl+F")
        fit_view_action.triggered.connect(self.image_view.fit_in_view)
        view_menu.addAction(fit_view_action)

        view_menu.addSeparator()

        circle_action = QAction("圆点显示", self)
        circle_action.setCheckable(True)
        circle_action.setChecked(True)
        circle_action.triggered.connect(lambda: self.toggle_display_style(True))
        view_menu.addAction(circle_action)

        cross_action = QAction("十字显示", self)
        cross_action.setCheckable(True)
        cross_action.triggered.connect(lambda: self.toggle_display_style(False))
        view_menu.addAction(cross_action)

        view_menu.addSeparator()

        label_action = QAction("显示编号", self)
        label_action.setCheckable(True)
        label_action.toggled.connect(self.toggle_labels)
        view_menu.addAction(label_action)

        # 设置菜单
        settings_menu = menubar.addMenu("设置")

        self.auto_save_action = QAction("自动保存", self)
        self.auto_save_action.setCheckable(True)
        self.auto_save_action.setChecked(True)
        self.auto_save_action.toggled.connect(self.toggle_auto_save)
        settings_menu.addAction(self.auto_save_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("工具栏")
        self.addToolBar(toolbar)

        # 导航按钮
        prev_action = QAction("上一张 (A)", self)
        prev_action.triggered.connect(self.previous_image)
        toolbar.addAction(prev_action)

        next_action = QAction("下一张 (D)", self)
        next_action.triggered.connect(self.next_image)
        toolbar.addAction(next_action)

        toolbar.addSeparator()

        # 缩放按钮
        zoom_in_action = QAction("放大 (+)", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction("缩小 (-)", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)

        fit_action = QAction("适应窗口", self)
        fit_action.triggered.connect(self.image_view.fit_in_view)
        toolbar.addAction(fit_action)

        toolbar.addSeparator()

        # 标注格式切换按钮
        self.format_action = QAction("标注格式：TXT", self)
        self.format_action.triggered.connect(self.toggle_annotation_format)
        toolbar.addAction(self.format_action)

    def toggle_annotation_format(self):
        """切换标注格式"""
        # 先保存当前格式的数据，避免切换时丢失未保存的修改
        if self.current_image_index >= 0 and self.keypoints_data:
            if self.auto_save:
                self.save_annotations()
            else:
                reply = QMessageBox.question(
                    self, '保存确认',
                    '切换格式前需要保存当前标注吗？',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self.save_annotations()

        if self.annotation_format == 'txt':
            self.annotation_format = 'json'
            self.format_action.setText("标注格式：JSON")
            self.status_label.setText("标注格式已切换为 JSON")
        else:
            self.annotation_format = 'txt'
            self.format_action.setText("标注格式：TXT")
            self.status_label.setText("标注格式已切换为 TXT")

        # 切换格式后，重新加载当前图片的标注
        if self.current_image_index >= 0 and self.current_image_index < len(self.image_files):
            image_path = self.image_files[self.current_image_index]
            self.load_annotations(image_path)

    def keyPressEvent(self, event):
        """快捷键处理"""
        if event.key() == Qt.Key_A:
            self.previous_image()
        elif event.key() == Qt.Key_D:
            self.next_image()
        elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self.delete_selected_keypoint()
        else:
            super().keyPressEvent(event)

    def open_directory(self):
        """打开目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择图片目录")
        if dir_path:
            self.current_dir = Path(dir_path)
            self.load_images_from_directory()

    def load_images_from_directory(self):
        """从目录加载图片"""
        if not self.current_dir:
            return

        # 支持的图片格式
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
        self.image_files = []

        for ext in extensions:
            self.image_files.extend(self.current_dir.glob(ext))
            self.image_files.extend(self.current_dir.glob(ext.upper()))

        self.image_files = sorted(list(set(self.image_files)))

        if self.image_files:
            self.current_image_index = 0
            self.load_current_image()
            self.status_label.setText(f"加载了 {len(self.image_files)} 张图片")
        else:
            QMessageBox.warning(self, "警告", "目录中没有找到图片文件")

    def load_current_image(self):
        """加载当前图片"""
        if self.current_image_index < 0 or self.current_image_index >= len(self.image_files):
            return

        # 加载新图片
        image_path = self.image_files[self.current_image_index]
        self.image_view.load_image(str(image_path))

        # 加载标注
        self.load_annotations(image_path)

        # 更新进度显示
        self.progress_label.setText(f"{self.current_image_index + 1}/{len(self.image_files)} - {image_path.name}")

        # 清空撤销/重做栈
        self.undo_stack.clear()
        self.redo_stack.clear()

    def load_annotations(self, image_path):
        """加载标注数据（根据当前格式设置加载）"""
        # 🔍 调试：打印加载前的状态
        print(f"[DEBUG] 加载标注前 keypoints_data 数量: {len(self.keypoints_data)}")

        self.keypoints_data.clear()
        self.image_view.clear_keypoints()

        # 根据当前选择的格式加载对应文件
        if self.annotation_format == 'json':
            json_path = image_path.with_suffix('.json')
            if json_path.exists():
                self._load_json_annotations(json_path)
            else:
                self.status_label.setText("未找到JSON标注文件，创建新标注")
        else:  # txt
            txt_path = image_path.with_suffix('.txt')
            if txt_path.exists():
                self._load_txt_annotations(txt_path)
            else:
                self.status_label.setText("未找到TXT标注文件，创建新标注")

        # 🔍 调试：打印加载后的状态
        print(f"[DEBUG] 加载标注后 keypoints_data 数量: {len(self.keypoints_data)}")
        print(f"[DEBUG] 关键点ID列表: {sorted(self.keypoints_data.keys())}")

        # 更新列表显示
        self.update_keypoint_list()

    def _load_json_annotations(self, json_path):
        """从JSON文件加载标注"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            keypoints = data.get('keypoints', [])
            loaded_count = 0
            for kp in keypoints:
                kp_id = kp['id']
                ratio_x = kp['x']
                ratio_y = kp['y']

                # 跳过未标注的点（-1, -1）
                if ratio_x < 0 or ratio_y < 0:
                    continue

                # 将比例坐标转换为像素坐标用于显示
                x, y = self.ratio_to_pixel(ratio_x, ratio_y)
                # 检查转换是否成功
                if x is None or y is None:
                    print(f"警告: 跳过关键点{kp_id}，坐标转换失败")
                    continue

                # 存储比例坐标
                self.keypoints_data[kp_id] = (ratio_x, ratio_y)
                # 使用像素坐标显示
                self.image_view.add_keypoint(kp_id, x, y)
                loaded_count += 1

            self.status_label.setText(f"加载了 {loaded_count} 个关键点 (JSON)")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "警告", f"加载JSON标注文件失败：{str(e)}")

    def _load_txt_annotations(self, txt_path):
        """从TXT文件加载标注"""
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            coords = content.split()
            coords = [float(c) for c in coords]

            if len(coords) != 136:  # 68个点 × 2坐标
                QMessageBox.warning(self, "警告", f"TXT文件格式错误：应包含136个坐标值，实际{len(coords)}个")
                return

            loaded_count = 0
            for i in range(68):
                kp_id = i + 1
                ratio_x = coords[i * 2]
                ratio_y = coords[i * 2 + 1]

                # 跳过未标注的点（-1, -1）
                if ratio_x < 0 or ratio_y < 0:
                    continue

                # 将比例坐标转换为像素坐标用于显示
                x, y = self.ratio_to_pixel(ratio_x, ratio_y)
                # 检查转换是否成功
                if x is None or y is None:
                    print(f"警告: 跳过关键点{kp_id}，坐标转换失败")
                    continue

                # 存储比例坐标
                self.keypoints_data[kp_id] = (ratio_x, ratio_y)
                # 使用像素坐标显示
                self.image_view.add_keypoint(kp_id, x, y)
                loaded_count += 1

            self.status_label.setText(f"加载了 {loaded_count} 个关键点 (TXT)")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "警告", f"加载TXT标注文件失败：{str(e)}")

    def save_annotations(self):
        """保存标注数据（根据annotation_format决定格式）"""
        if self.current_image_index < 0 or self.current_image_index >= len(self.image_files):
            return

        image_path = self.image_files[self.current_image_index]

        # 🔍 调试：打印保存时的关键点数量
        print(f"[DEBUG] 保存图片: {image_path.name}, 关键点数量: {len(self.keypoints_data)}")
        print(f"[DEBUG] 关键点ID列表: {sorted(self.keypoints_data.keys())}")

        if self.annotation_format == 'json':
            self._save_json_annotations(image_path)
        else:  # txt
            self._save_txt_annotations(image_path)

    def _save_json_annotations(self, image_path):
        """保存为JSON格式"""
        json_path = image_path.with_suffix('.json')

        # 构建JSON数据（使用比例坐标）
        keypoints = []
        for kp_id in range(1, 69):
            if kp_id in self.keypoints_data:
                ratio_x, ratio_y = self.keypoints_data[kp_id]
            else:
                # 未标注的点使用-1表示（不可见/未标注）
                ratio_x, ratio_y = -1.0, -1.0

            keypoints.append({
                'id': kp_id,
                'x': round(ratio_x, 6),  # 保留6位小数
                'y': round(ratio_y, 6)
            })

        data = {
            'image_name': image_path.name,
            'keypoints': keypoints
        }

        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.status_label.setText("标注已保存 (JSON)")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存JSON标注失败：{str(e)}")

    def _save_txt_annotations(self, image_path):
        """保存为TXT格式（136个坐标值，空格分隔）"""
        txt_path = image_path.with_suffix('.txt')

        # 构建TXT数据：68个点的x y坐标，空格分隔
        coords = []
        for kp_id in range(1, 69):
            if kp_id in self.keypoints_data:
                ratio_x, ratio_y = self.keypoints_data[kp_id]
                coords.append(f"{ratio_x:.6f}")
                coords.append(f"{ratio_y:.6f}")
            else:
                # 如果某个点未标注，使用-1.0表示（不可见/未标注）
                coords.append("-1.000000")
                coords.append("-1.000000")

        txt_content = ' '.join(coords)

        try:
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(txt_content)
            self.status_label.setText("标注已保存 (TXT)")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存TXT标注失败：{str(e)}")

    def previous_image(self):
        """上一张图片"""
        if self.current_image_index > 0:
            # 处理所有待处理的事件（确保鼠标释放事件已完成）
            QApplication.processEvents()

            # 保存当前图片的标注（如果开启了自动保存）
            # 使用当前索引显式保存，避免竞态条件
            if self.auto_save:
                current_index = self.current_image_index  # 保存当前索引
                self.save_annotations()
                # 确保保存的是正确的图片
                assert self.current_image_index == current_index, "索引在保存过程中被改变！"

            self.current_image_index -= 1
            self.load_current_image()

    def next_image(self):
        """下一张图片"""
        if self.current_image_index < len(self.image_files) - 1:
            # 处理所有待处理的事件（确保鼠标释放事件已完成）
            QApplication.processEvents()

            # 保存当前图片的标注（如果开启了自动保存）
            # 使用当前索引显式保存，避免竞态条件
            if self.auto_save:
                current_index = self.current_image_index  # 保存当前索引
                self.save_annotations()
                # 确保保存的是正确的图片
                assert self.current_image_index == current_index, "索引在保存过程中被改变！"

            self.current_image_index += 1
            self.load_current_image()

    def zoom_in(self):
        """放大"""
        if self.image_view.current_scale * 1.2 <= self.image_view.max_scale:
            self.image_view.scale(1.2, 1.2)
            self.image_view.current_scale *= 1.2

    def zoom_out(self):
        """缩小"""
        if self.image_view.current_scale / 1.2 >= self.image_view.min_scale:
            self.image_view.scale(1/1.2, 1/1.2)
            self.image_view.current_scale /= 1.2

    def toggle_display_style(self, show_circle):
        """切换显示样式"""
        self.image_view.toggle_display_style(show_circle)
        self.reference_view.toggle_display_style(show_circle)

    def toggle_labels(self, show):
        """切换标签显示"""
        self.image_view.toggle_labels(show)
        self.reference_view.toggle_labels(show)

    def toggle_auto_save(self, enabled):
        """切换自动保存"""
        self.auto_save = enabled

    def show_about_dialog(self):
        """显示关于对话框"""
        about_text = """
<h2>68 Keypoints Annotation Tool</h2>
<p><b>作者:</b> pellykoo</p>
<p><b>版本:</b> 1.0.0</p>

<h3>快捷键说明:</h3>
<table cellpadding="5">
<tr><td><b>A</b></td><td>上一张图片</td></tr>
<tr><td><b>D</b></td><td>下一张图片</td></tr>
<tr><td><b>Ctrl+Z</b></td><td>撤销</td></tr>
<tr><td><b>Ctrl+Y</b></td><td>重做</td></tr>
<tr><td><b>Ctrl+S</b></td><td>手动保存</td></tr>
<tr><td><b>Ctrl+R</b></td><td>清空标注</td></tr>
<tr><td><b>Delete</b></td><td>删除选中点</td></tr>
<tr><td><b>滚轮</b></td><td>缩放图片</td></tr>
<tr><td><b>鼠标拖动</b></td><td>平移图片</td></tr>
</table>
        """
        QMessageBox.about(self, "关于", about_text)

    def on_keypoint_added(self, kp_id, x, y):
        """关键点添加事件（x, y为像素坐标）"""
        # 保存状态用于撤销
        self.save_state()

        # 将像素坐标转换为比例坐标存储
        ratio_x, ratio_y = self.pixel_to_ratio(x, y)
        # 检查转换是否成功
        if ratio_x is None or ratio_y is None:
            self.status_label.setText("错误: 无法保存关键点，图片未正确加载")
            return

        self.keypoints_data[kp_id] = (ratio_x, ratio_y)
        self.update_keypoint_list()

        # 修改逻辑：不在这里保存，而是在切换图片/关闭窗口时保存
        # if self.auto_save:
        #     self.save_annotations()

    def on_keypoint_moved(self, kp_id, x, y):
        """关键点移动事件（x, y为像素坐标）"""
        # 🔍 调试：打印移动事件
        print(f"[DEBUG] 关键点移动: ID={kp_id}, 像素坐标=({x:.2f}, {y:.2f})")

        # 保存状态用于撤销
        self.save_state()

        # 将像素坐标转换为比例坐标存储
        ratio_x, ratio_y = self.pixel_to_ratio(x, y)
        # 检查转换是否成功
        if ratio_x is None or ratio_y is None:
            self.status_label.setText("错误: 无法保存关键点，图片未正确加载")
            return

        self.keypoints_data[kp_id] = (ratio_x, ratio_y)
        print(f"[DEBUG] 更新后 keypoints_data 数量: {len(self.keypoints_data)}")
        self.update_keypoint_list()

        # 修改逻辑：不在这里保存，而是在切换图片/关闭窗口时保存
        # if self.auto_save:
        #     self.save_annotations()

    def on_keypoint_selected(self, kp_id):
        """关键点选中事件"""
        if kp_id > 0:
            self.image_view.select_keypoint(kp_id)
            self.keypoint_list.setCurrentRow(kp_id - 1)

            # 同步选中参考图中的关键点
            if kp_id in self.reference_keypoints:
                self.reference_view.select_keypoint(kp_id)

    def on_reference_keypoint_selected(self, kp_id):
        """参考图关键点选中事件"""
        if kp_id > 0:
            self.reference_view.select_keypoint(kp_id)
            self.keypoint_list.setCurrentRow(kp_id - 1)

            # 同步选中主图中的关键点
            if kp_id in self.keypoints_data:
                self.image_view.select_keypoint(kp_id)

    def on_list_item_clicked(self, item):
        """列表项点击事件"""
        kp_id = self.keypoint_list.row(item) + 1

        if kp_id in self.keypoints_data:
            # 选中该关键点
            self.image_view.select_keypoint(kp_id)
            if kp_id in self.reference_keypoints:
                self.reference_view.select_keypoint(kp_id)
        else:
            # 进入添加模式
            self.image_view.set_adding_mode(kp_id)
            self.status_label.setText(f"请在图片上点击以添加第 {kp_id} 个关键点")

    def update_keypoint_list(self):
        """更新关键点列表显示（显示比例坐标）"""
        for i in range(1, 69):
            item = self.keypoint_list.item(i - 1)
            if i in self.keypoints_data:
                ratio_x, ratio_y = self.keypoints_data[i]
                item.setText(f"{i}: ({ratio_x:.4f}, {ratio_y:.4f})")  # 显示4位小数的比例
                item.setForeground(QColor(0, 0, 0))  # 已标注显示黑色
            else:
                item.setText(f"{i}: 未标注")
                item.setForeground(QColor(255, 100, 100))  # 未标注显示红色

    def delete_selected_keypoint(self):
        """删除选中的关键点"""
        current_row = self.keypoint_list.currentRow()
        if current_row >= 0:
            kp_id = current_row + 1
            if kp_id in self.keypoints_data:
                # 保存状态用于撤销
                self.save_state()

                del self.keypoints_data[kp_id]
                self.image_view.remove_keypoint(kp_id)
                self.update_keypoint_list()

                # 修改逻辑：不在这里保存，而是在切换图片/关闭窗口时保存
                # if self.auto_save:
                #     self.save_annotations()

                self.status_label.setText(f"已删除第 {kp_id} 个关键点")

    def swap_keypoints(self, id1, id2):
        """交换两个关键点的位置"""
        # 保存状态用于撤销
        self.save_state()

        pos1 = self.keypoints_data.get(id1)
        pos2 = self.keypoints_data.get(id2)

        # 交换数据（已经是比例坐标）
        if pos1 and pos2:
            self.keypoints_data[id1] = pos2
            self.keypoints_data[id2] = pos1
        elif pos1:
            self.keypoints_data[id2] = pos1
            del self.keypoints_data[id1]
        elif pos2:
            self.keypoints_data[id1] = pos2
            del self.keypoints_data[id2]

        # 更新显示（需要转换为像素坐标）
        self.image_view.clear_keypoints()
        for kp_id, (ratio_x, ratio_y) in self.keypoints_data.items():
            x, y = self.ratio_to_pixel(ratio_x, ratio_y)
            self.image_view.add_keypoint(kp_id, x, y)

        self.update_keypoint_list()

        # 修改逻辑：不在这里保存，而是在切换图片/关闭窗口时保存
        # if self.auto_save:
        #     self.save_annotations()

        self.status_label.setText(f"已交换第 {id1} 和 {id2} 个关键点")

    def save_state(self):
        """保存当前状态用于撤销"""
        state = self.keypoints_data.copy()
        self.undo_stack.append(state)

        # 限制撤销栈大小
        if len(self.undo_stack) > self.max_undo_steps:
            self.undo_stack.pop(0)

        # 清空重做栈
        self.redo_stack.clear()

    def undo(self):
        """撤销"""
        if self.undo_stack:
            # 保存当前状态到重做栈
            self.redo_stack.append(self.keypoints_data.copy())

            # 恢复上一个状态
            self.keypoints_data = self.undo_stack.pop()

            # 更新显示（转换比例坐标为像素坐标）
            self.image_view.clear_keypoints()
            for kp_id, (ratio_x, ratio_y) in self.keypoints_data.items():
                x, y = self.ratio_to_pixel(ratio_x, ratio_y)
                # 检查转换是否成功
                if x is not None and y is not None:
                    self.image_view.add_keypoint(kp_id, x, y)

            self.update_keypoint_list()

            # 移除auto_save: 撤销操作不应该自动保存，避免误触撤销后覆盖正确的数据
            # 用户可以手动Ctrl+S保存撤销后的状态

            self.status_label.setText("已撤销（未自动保存，如需保存请按Ctrl+S）")
        else:
            self.status_label.setText("没有可撤销的操作")

    def redo(self):
        """重做"""
        if self.redo_stack:
            # 保存当前状态到撤销栈
            self.undo_stack.append(self.keypoints_data.copy())

            # 恢复重做状态
            self.keypoints_data = self.redo_stack.pop()

            # 更新显示（转换比例坐标为像素坐标）
            self.image_view.clear_keypoints()
            for kp_id, (ratio_x, ratio_y) in self.keypoints_data.items():
                x, y = self.ratio_to_pixel(ratio_x, ratio_y)
                # 检查转换是否成功
                if x is not None and y is not None:
                    self.image_view.add_keypoint(kp_id, x, y)

            self.update_keypoint_list()

            # 移除auto_save: 重做操作不应该自动保存，避免误触重做后覆盖正确的数据
            # 用户可以手动Ctrl+S保存重做后的状态

            self.status_label.setText("已重做（未自动保存，如需保存请按Ctrl+S）")
        else:
            self.status_label.setText("没有可重做的操作")

    def clear_annotations(self):
        """清空当前图片的所有标注"""
        reply = QMessageBox.question(
            self, '确认清空',
            '确定要清空当前图片的所有标注吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 保存状态用于撤销
            self.save_state()

            self.keypoints_data.clear()
            self.image_view.clear_keypoints()
            self.update_keypoint_list()

            # 修改逻辑：不在这里保存，而是在切换图片/关闭窗口时保存
            # if self.auto_save:
            #     self.save_annotations()

            self.status_label.setText("已清空所有标注")

    def select_reference_image(self):
        """选择标准参考图"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择标准参考图",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp)"
        )

        if file_path:
            self.load_reference_image(file_path)

    def load_reference_image(self, image_path):
        """加载标准参考图"""
        self.reference_image_path = Path(image_path)
        self.reference_view.load_image(str(self.reference_image_path))

        # 根据图片宽高比调整参考视图的显示尺寸
        img_width, img_height = self.reference_view.get_image_size()
        if img_width and img_height:
            aspect_ratio = img_width / img_height

            # 设置合适的显示高度（可以根据需要调整基准高度）
            base_height = 400  # 基准高度
            optimal_height = base_height
            optimal_width = int(base_height * aspect_ratio)

            # 设置最小和最大限制
            min_height = 300
            max_height = 600
            min_width = 200
            max_width = 500

            # 应用限制
            optimal_height = max(min_height, min(max_height, optimal_height))
            optimal_width = max(min_width, min(max_width, optimal_width))

            # 根据宽度重新计算高度以保持比例
            if optimal_width == max_width or optimal_width == min_width:
                optimal_height = int(optimal_width / aspect_ratio)
                optimal_height = max(min_height, min(max_height, optimal_height))

            self.reference_view.setMinimumHeight(optimal_height)
            self.reference_view.setMinimumWidth(optimal_width)

        # 尝试加载对应的JSON文件
        json_path = self.reference_image_path.with_suffix('.json')
        self.reference_keypoints.clear()

        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                keypoints = data.get('keypoints', [])
                for kp in keypoints:
                    kp_id = kp['id']
                    ratio_x = kp['x']
                    ratio_y = kp['y']

                    # 将比例坐标转换为像素坐标
                    pixel_x = ratio_x * img_width
                    pixel_y = ratio_y * img_height

                    self.reference_keypoints[kp_id] = (ratio_x, ratio_y)
                    self.reference_view.add_keypoint(kp_id, pixel_x, pixel_y)

                self.status_label.setText(f"标准图加载了 {len(keypoints)} 个关键点")
            except Exception as e:
                self.status_label.setText(f"标准图JSON加载失败：{str(e)}")
        else:
            self.status_label.setText("标准图没有对应的JSON文件")

        # 确保参考图完整显示在视图内，不出现滚动条
        self.reference_view.fit_in_view()

    def closeEvent(self, event):
        """窗口关闭事件 - 保存当前标注"""
        if self.auto_save and self.current_image_index >= 0:
            self.save_annotations()
        event.accept()


def main():
    app = QApplication(sys.argv)

    # 设置应用程序图标
    icon_path = get_resource_path('keypoints.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()

    # 设置窗口图标（任务栏图标）
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))

    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
