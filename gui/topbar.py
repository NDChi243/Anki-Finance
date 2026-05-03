# -*- coding: utf-8 -*-

from aqt.qt import QWidget, QHBoxLayout, QLabel, QPushButton, Qt
from aqt.qt import QTimer


class TycoonTopBar(QWidget):
    """
    Thanh mỏng chỉ cao ~28px, không chiếm nhiều diện tích.
    Hiển thị: icon | số dư | năng lượng | nút update (badge) | nút mở
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            TycoonTopBar {
                background: #0f0f18;
                border-bottom: 1px solid #2a2a40;
            }
            QLabel {
                color: #94a3b8;
                background: transparent;
                font-size: 11px;
            }
            QLabel#brand {
                color: #7c3aed;
                font-weight: 700;
                font-size: 11px;
            }
            QLabel#bal {
                color: #10b981;
                font-weight: 800;
                font-size: 12px;
            }
            QLabel#energy {
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton {
                background: transparent;
                border: 1px solid #3a3a55;
                border-radius: 4px;
                color: #a78bfa;
                font-size: 11px;
                font-weight: 600;
                padding: 1px 8px;
                min-height: 18px;
                max-height: 20px;
            }
            QPushButton:hover {
                background: rgba(124,58,237,0.2);
                border-color: #7c3aed;
            }
            QPushButton#updateBtn {
                border-color: #ef4444;
                color: #fca5a5;
                font-size: 10px;
                padding: 1px 6px;
            }
            QPushButton#updateBtn:hover {
                background: rgba(239,68,68,0.2);
                border-color: #ef4444;
            }
            QPushButton#updateBtn:disabled {
                border-color: #3a3a55;
                color: #6b7280;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        brand = QLabel("🎓 Anki Finance")
        brand.setObjectName("brand")
        layout.addWidget(brand)

        # ── Rank label ──
        self.rank_label = QLabel("📚 SV1")
        self.rank_label.setStyleSheet("""
            color: #a78bfa;
            background: transparent;
            font-size: 10px;
            font-weight: 600;
            padding: 0px;
        """)
        self.rank_label.setToolTip("Cấp bậc hiện tại")
        layout.addWidget(self.rank_label)

        # ── Version label ──
        from ..auto_update import get_current_version
        self.version_label = QLabel(f"v{get_current_version()}")
        self.version_label.setStyleSheet("""
            color: #5a5a7a;
            background: transparent;
            font-size: 9px;
            font-weight: 400;
            padding: 0px;
        """)
        self.version_label.setToolTip("Phiên bản hiện tại — auto-update sẽ tự động cập nhật khi có bản mới")
        layout.addWidget(self.version_label)

        sep = QLabel("·")
        sep.setStyleSheet("color: #3a3a55; background: transparent;")
        layout.addWidget(sep)

        # ── EXP label ──
        self.exp_label = QLabel("⭐ 0 XP")
        self.exp_label.setStyleSheet("""
            color: #f59e0b;
            background: transparent;
            font-size: 10px;
            font-weight: 600;
            padding: 0px;
        """)
        self.exp_label.setToolTip("Điểm EXP tích lũy")
        layout.addWidget(self.exp_label)

        sep_exp = QLabel("·")
        sep_exp.setStyleSheet("color: #3a3a55; background: transparent;")
        layout.addWidget(sep_exp)

        # ── KN label ──
        self.kn_label = QLabel("🧠 0 KN")
        self.kn_label.setStyleSheet("""
            color: #10b981;
            background: transparent;
            font-size: 10px;
            font-weight: 600;
            padding: 0px;
        """)
        self.kn_label.setToolTip("Điểm Kiến Thức (KN)")
        layout.addWidget(self.kn_label)

        sep2 = QLabel("·")
        sep2.setStyleSheet("color: #3a3a55; background: transparent;")
        layout.addWidget(sep2)

        layout.addWidget(QLabel("💰"))

        self.balance_label = QLabel("0 VND")
        self.balance_label.setObjectName("bal")
        self.balance_label.setToolTip("Đang tải…")
        layout.addWidget(self.balance_label)

        # ── Energy indicator ──
        sep2 = QLabel("·")
        sep2.setStyleSheet("color: #3a3a55; background: transparent;")
        layout.addWidget(sep2)

        layout.addWidget(QLabel("⚡"))

        self.energy_label = QLabel("100%")
        self.energy_label.setObjectName("energy")
        self.energy_label.setStyleSheet("color: #f59e0b; background: transparent; font-weight: 600;")
        self.energy_label.setToolTip("Năng lượng học tập — ⚠️ Hết năng lượng = ×0.5 tiền thưởng")
        layout.addWidget(self.energy_label)

        # ── Vehicle indicator ──
        self._sep_vehicle = QLabel("·")
        self._sep_vehicle.setStyleSheet("color: #3a3a55; background: transparent;")
        layout.addWidget(self._sep_vehicle)
        self._sep_vehicle.hide()

        self._vehicle_label = QLabel("—")
        self._vehicle_label.setObjectName("vehicle")
        self._vehicle_label.setStyleSheet("color: #475569; background: transparent; font-size: 11px;")
        self._vehicle_label.setToolTip("Không có xe nào đang sử dụng")
        layout.addWidget(self._vehicle_label)

        layout.addStretch()

        # ── Nút cập nhật (badge đỏ) ──
        self.update_btn = QPushButton("🔄 Cập nhật")
        self.update_btn.setObjectName("updateBtn")
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.clicked.connect(self._on_update_clicked)
        self.update_btn.hide()  # ẩn mặc định, chỉ hiện khi có bản cập nhật
        layout.addWidget(self.update_btn)

        # ── Nút mở chính ──
        btn = QPushButton("Anki Finance ↗")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._open_window)
        layout.addWidget(btn)

        self._window = None

        # Timer tự động refresh mỗi 5 giây để check update flag
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start(5000)

        self.refresh()

    def refresh(self):
        try:
            from ..balance import get_balance, get_stats
            bal = get_balance() or 0

            # ── Cập nhật EXP, KN, Rank ──
            try:
                from ..rank_system import get_xp, get_kn, get_rank_status
                xp = get_xp()
                kn = get_kn()
                rank = get_rank_status(bal)
                self.exp_label.setText(f"⭐ {xp:,} EXP".replace(",", "."))
                self.kn_label.setText(f"🧠 {kn:,} KN".replace(",", "."))
                rl = rank.get("rank_label", "—")
                re = rank.get("rank_emoji", "📚")
                self.rank_label.setText(f"{re} {rl[:12]}")
                self.rank_label.setToolTip(
                    f"🎖️ Rank: {rank['rank_label']}\n"
                    f"⭐ EXP: {xp:,}\n"
                    f"🧠 KN: {kn:,}\n"
                    f"📊 Tiến độ: {rank['overall_pct']}%"
                )
            except Exception:
                pass
            self.balance_label.setText(f"{bal:,} VND".replace(",", "."))
            # Tooltip: quick stats
            stats = get_stats() or {}
            streak = stats.get("streak_days", 0)
            total_earned = stats.get("total_earned", 0)
            reviews = stats.get("total_reviews", 0)
            try:
                from ..streak_system import get_streak_status
                s = get_streak_status()
                mult = s.get("multiplier", 1.0)
            except Exception:
                mult = 1.0
            try:
                from ..rank_system import get_rank_status
                rank = get_rank_status(bal)
                rank_label = rank.get("rank_label", "—")
            except Exception:
                rank_label = "—"
            self.balance_label.setToolTip(
                f"🔥 Streak: {streak} ngày (×{mult:.1f})\n"
                f"⭐ Rank: {rank_label}\n"
                f"📝 Đã ôn: {reviews:,} thẻ\n"
                f"💵 Tổng kiếm: {total_earned:,}đ".replace(",", ".")
            )

            # ── Cập nhật energy ──
            try:
                from ..energy_system import get_energy_status
                eng = get_energy_status()
                pct = eng["percent"]
                self.energy_label.setText(f"{pct:.0f}%")
                if pct <= 0:
                    self.energy_label.setStyleSheet("color: #ef4444; background: transparent; font-weight: 700;")
                elif pct <= 25:
                    self.energy_label.setStyleSheet("color: #f97316; background: transparent; font-weight: 600;")
                elif pct <= 50:
                    self.energy_label.setStyleSheet("color: #f59e0b; background: transparent; font-weight: 600;")
                else:
                    self.energy_label.setStyleSheet("color: #10b981; background: transparent; font-weight: 600;")
                self.energy_label.setToolTip(
                    f"⚡ Năng lượng: {eng['current']}/{eng['max']} ({pct:.0f}%)\n"
                    f"{'⚠️ Kiệt sức! ×0.5 tiền thưởng' if eng['exhausted'] else '✅ Học tập hiệu quả'}\n"
                    "⏳ Hồi 1 điểm mỗi 30 phút"
                )
            except Exception:
                self.energy_label.setText("?%")
        except Exception:
            self.balance_label.setText("0 VND")
            self.balance_label.setToolTip("⚠️ Không thể tải thông tin")
            self.energy_label.setText("?%")

        # ── Cập nhật vehicle indicator ──
        try:
            from ..vehicle_system import get_active_vehicle
            av = get_active_vehicle()
            if av:
                item_id   = av.get("vehicle_id") or av.get("item_id", "")
                fuel_type = av.get("fuel_type", "gasoline")
                dur       = av.get("durability", 0)
                max_dur   = av.get("max_durability", 1)
                max_fuel  = av.get("max_fuel", 0)
                fuel_lvl  = av.get("fuel_level", 0)
                dur_pct   = int(dur / max_dur * 100) if max_dur > 0 else 0
                fuel_pct  = int(fuel_lvl / max_fuel * 100) if max_fuel > 0 else 100

                from ..shop_data import load_shop_items
                items_map = {i["id"]: i for i in load_shop_items()}
                item_data = items_map.get(item_id, {})
                vname     = item_data.get("name", item_id)
                emoji     = item_data.get("emoji", "🚗")

                if fuel_type == "manual":
                    self._vehicle_label.setText(f"{emoji} {dur_pct}%")
                elif fuel_type == "electric":
                    self._vehicle_label.setText(f"{emoji} ⚡{fuel_pct}%")
                else:
                    self._vehicle_label.setText(f"{emoji} ⛽{fuel_pct}%")

                # Màu theo độ bền: đỏ < 20%, vàng < 50%, xanh >= 50%
                if dur_pct < 20:
                    color = "#ef4444"
                elif dur_pct < 50:
                    color = "#f59e0b"
                else:
                    color = "#10b981"
                self._vehicle_label.setStyleSheet(
                    f"color: {color}; background: transparent; font-size: 11px; font-weight: 600;"
                )
                fuel_label = "⚡ Điện" if fuel_type == "electric" else ("— (Xe đạp)" if fuel_type == "manual" else "⛽ Xăng")
                self._vehicle_label.setToolTip(
                    f"🚗 Đang lái: {vname}\n"
                    f"🔧 Độ bền: {dur_pct}%\n"
                    f"{fuel_label}: {fuel_pct}%"
                )
                self._sep_vehicle.show()
            else:
                self._vehicle_label.setText("—")
                self._vehicle_label.setStyleSheet(
                    "color: #475569; background: transparent; font-size: 11px;"
                )
                self._vehicle_label.setToolTip("Không có xe nào đang sử dụng")
                self._sep_vehicle.hide()
        except Exception:
            self._vehicle_label.setText("—")
            self._sep_vehicle.hide()

        # ── Kiểm tra trạng thái cập nhật ──
        self._check_update_status()

    def _check_update_status(self):
        """Kiểm tra flag cập nhật từ auto_update module và hiển thị badge."""
        try:
            from ..auto_update import (
                is_update_available,
                get_pending_update_info,
                _UPDATE_DOWNLOADING,
                _PENDING_RESTART,
                _schedule_anki_restart,
                _reset_pending_restart,
            )

            # ── Ưu tiên 1: Đã có bản cập nhật đã cài, chờ restart ──
            if _PENDING_RESTART:
                self.update_btn.setText("✅ Đã cập nhật! Đang khởi động lại...")
                self.update_btn.setEnabled(False)
                self.update_btn.show()
                # Lên lịch restart từ main thread (timer Qt an toàn)
                _schedule_anki_restart(delay_seconds=3)
                # Reset flag để không schedule nhiều lần
                _reset_pending_restart()
                return

            # ── Ưu tiên 2: Có bản cập nhật chờ xử lý ──
            has_update = is_update_available()
            if has_update:
                info = get_pending_update_info()
                if info:
                    old_v = info.get("local_version", "?")
                    new_v = info.get("latest_version", "?")
                    self.update_btn.setText(f"🔴 v{old_v} → v{new_v}")
                    self.update_btn.setToolTip(
                        f"Có bản cập nhật mới!\n"
                        f"v{old_v} → v{new_v}\n"
                        f"Bấm để tải về và cài đặt."
                    )
                    self.update_btn.setEnabled(True)
                    self.update_btn.show()
                else:
                    self.update_btn.hide()
                return

            # ── Ưu tiên 3: Đang tải ──
            if _UPDATE_DOWNLOADING:
                self.update_btn.setText("⏳ Đang tải...")
                self.update_btn.setEnabled(False)
                self.update_btn.show()
                return

            # ── Mặc định: ẩn nút ──
            self.update_btn.hide()

        except Exception:
            self.update_btn.hide()

    def _on_update_clicked(self):
        """Người dùng bấm nút cập nhật → xác nhận → tải → restart."""
        try:
            from aqt.utils import tooltip, showInfo
            from ..auto_update import get_pending_update_info

            info = get_pending_update_info()
            if not info:
                tooltip("⚠️ Không có bản cập nhật nào.", period=3000)
                return

            old_v = info.get("local_version", "?")
            new_v = info.get("latest_version", "?")

            # Xác nhận với người dùng
            reply = showInfo(
                f"🔄 Cập nhật Anki Finance\n\n"
                f"Phiên bản hiện tại: v{old_v}\n"
                f"Phiên bản mới:      v{new_v}\n\n"
                f"Tiến trình của bạn sẽ được giữ nguyên.\n"
                f"Anki sẽ tự động khởi động lại sau khi cập nhật.\n\n"
                f"Bấm OK để bắt đầu cập nhật."
            )

            # showInfo không trả về giá trị, nó chỉ hiển thị dialog OK.
            # Nếu user bấm OK (không có Huỷ), ta tiến hành cập nhật.
            self.update_btn.setText("⏳ Đang tải...")
            self.update_btn.setEnabled(False)

            from ..auto_update import confirm_and_apply_update
            result = confirm_and_apply_update()

            if not result.get("ok"):
                tooltip(f"❌ {result.get('error', 'Cập nhật thất bại')}", period=5000)
                self._check_update_status()
        except Exception as e:
            from aqt.utils import tooltip
            tooltip(f"❌ Lỗi: {e}", period=5000)
            self._check_update_status()

    def _open_window(self):
        from .webview_window import TycoonWindow
        from aqt import mw
        if self._window is None:
            self._window = TycoonWindow(mw)
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()
