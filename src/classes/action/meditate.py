from __future__ import annotations

import random
from src.i18n import t
from src.classes.action import TimedAction
from src.classes.event import Event
from src.systems.cultivation import REALM_RANK

class Meditate(TimedAction):
    """
    Thiền định (Tu luyện Phật môn): Không phụ thuộc vào linh khí, thông qua ngồi thiền để bình ổn tâm cảnh, có xác suất đốn ngộ nhận được lượng lớn tu vi.
    """
    
    # ID Đa ngôn ngữ
    ACTION_NAME_ID = "meditate_action_name"
    DESC_ID = "meditate_description"
    REQUIREMENTS_ID = "meditate_requirements"
    
    # Các hằng số không cần dịch
    EMOJI = "🧘"
    PARAMS = {}

    duration_months = 3
    
    # Các hằng số kinh nghiệm
    BASE_EXP = 10       # Kinh nghiệm thiền định thông thường (rất ít)
    EPIPHANY_EXP = 1500 # Kinh nghiệm đốn ngộ (rất nhiều, giá trị kỳ vọng khoảng 50/tháng)
    BASE_PROB = 0.1     # Xác suất đốn ngộ cơ bản 10%

    def _execute(self) -> None:
        """
        Logic thực hiện thiền định
        """
        # Kiểm tra bình cảnh
        if self.avatar.cultivation_progress.is_in_bottleneck():
            return

        # Tính toán hệ số cảnh giới (1, 2, 3, 4)
        realm = self.avatar.cultivation_progress.realm
        realm_multiplier = REALM_RANK.get(realm, 0) + 1
        
        # Tính toán xác suất đốn ngộ
        prob = self.BASE_PROB + float(self.avatar.effects.get("extra_meditate_prob", 0.0))
        
        # Xác định có đốn ngộ hay không
        is_epiphany = random.random() < prob
        
        base_exp = self.EPIPHANY_EXP if is_epiphany else self.BASE_EXP
        
        # Tính toán kinh nghiệm cuối cùng
        exp = int(base_exp * realm_multiplier)
        
        # Thưởng thêm
        multiplier = float(self.avatar.effects.get("extra_meditate_exp_multiplier", 0.0))
        if multiplier > 0:
            exp = int(exp * (1 + multiplier))
            
        self.avatar.cultivation_progress.add_exp(exp)
        
        # Ghi lại kết quả để dùng cho sự kiện
        self._last_is_epiphany = is_epiphany
        self._last_exp = exp

    def can_start(self) -> tuple[bool, str]:
        # 1. Kiểm tra bình cảnh
        if not self.avatar.cultivation_progress.can_cultivate():
            return False, t("Cultivation has reached bottleneck, cannot continue cultivating")
        
        # 2. Kiểm tra quyền hạn (Phải có quyền Meditate)
        legal = self.avatar.effects.get("legal_actions", [])
        if "Meditate" not in legal:
             return False, t("Your orthodoxy does not support Zen Meditation.")
             
        return True, ""

    def start(self) -> Event:
        # Ghi lại thời gian bắt đầu
        content = t("{avatar} begins Zen Meditation.", avatar=self.avatar.name)
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])

    async def finish(self) -> list[Event]:
        # Khi kết thúc, tạo các nhật ký khác nhau tùy vào việc có đốn ngộ hay không
        if getattr(self, '_last_is_epiphany', False):
            content = t("{avatar} had an epiphany during meditation! Cultivation increased significantly (+{exp}).", 
                       avatar=self.avatar.name, exp=getattr(self, '_last_exp', 0))
        else:
            content = t("{avatar} completed meditation with a peaceful mind.", 
                       avatar=self.avatar.name)
            
        return [Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])]
