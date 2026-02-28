from __future__ import annotations

from src.i18n import t
from src.classes.action import TimedAction
from src.classes.event import Event
from src.classes.root import get_essence_types_for_root
from src.classes.environment.region import CultivateRegion


class Respire(TimedAction):
    """
    Hành động Thổ nạp, có thể tăng tiến độ tu tiên (Tu vi).
    """
    
    # ID Đa ngôn ngữ
    ACTION_NAME_ID = "respire_action_name"
    DESC_ID = "respire_description"
    REQUIREMENTS_ID = "respire_requirements"
    
    # Các hằng số không cần dịch
    EMOJI = "🌀"
    PARAMS = {}

    duration_months = 10
    
    # Các hằng số kinh nghiệm
    BASE_EXP_PER_DENSITY = 100   # Kinh nghiệm cơ bản cho mỗi điểm mật độ linh khí tại vùng tu luyện
    BASE_EXP_LOW_EFFICIENCY = 50 # Kinh nghiệm cơ bản khi không khớp linh khí hoặc không phải vùng tu luyện

    def _execute(self) -> None:
        """
        Thực hiện Thổ nạp
        Lượng kinh nghiệm (exp) nhận được phụ thuộc vào loại khu vực và mức độ phù hợp của linh khí:
        - Vùng tu luyện + Linh khí phù hợp: exp = BASE_EXP_PER_DENSITY * density
        - Vùng tu luyện + Không khớp linh khí HOẶC Không phải vùng tu luyện: exp = BASE_EXP_LOW_EFFICIENCY
        """
        if self.avatar.cultivation_progress.is_in_bottleneck():
            return
            
        exp = self._calculate_base_exp()
        
        # Kết toán kinh nghiệm thổ nạp bổ sung (từ công pháp/tông môn/linh căn, v.v.)
        extra_exp = int(self.avatar.effects.get("extra_respire_exp", 0) or 0)
        if extra_exp:
            exp += extra_exp

        # Kết toán hệ số kinh nghiệm thổ nạp bổ sung
        multiplier = float(self.avatar.effects.get("extra_respire_exp_multiplier", 0.0) or 0.0)
        if multiplier > 0:
            exp = int(exp * (1 + multiplier))
            
        self.avatar.cultivation_progress.add_exp(exp)

    def _get_matched_essence_density(self) -> int:
        """
        Lấy mật độ linh khí phù hợp với linh căn của nhân vật tại khu vực hiện tại.
        Nếu không ở vùng tu luyện hoặc không có linh khí phù hợp, trả về 0.
        """
        region = self.avatar.tile.region
        if not isinstance(region, CultivateRegion):
            return 0
        essence_types = get_essence_types_for_root(self.avatar.root)
        return max((region.essence.get_density(et) for et in essence_types), default=0)

    def _calculate_base_exp(self) -> int:
        """
        Tính toán kinh nghiệm cơ bản dựa trên loại khu vực và mức độ phù hợp của linh khí
        """
        density = self._get_matched_essence_density()
        if density > 0:
            return self.BASE_EXP_PER_DENSITY * density
        return self.BASE_EXP_LOW_EFFICIENCY

    def can_start(self) -> tuple[bool, str]:
        # Kiểm tra bình cảnh
        if not self.avatar.cultivation_progress.can_cultivate():
            return False, t("Cultivation has reached bottleneck, cannot continue cultivating")
            
        # Kiểm tra quyền hạn (Đạo môn hoặc Tán tu)
        # Nếu legal_actions không trống và không chứa "Respire", thì cấm (nghĩa là thuộc các đạo thống khác như Phật/Nho)
        legal = self.avatar.effects.get("legal_actions", [])
        if legal and "Respire" not in legal:
            return False, t("Your orthodoxy does not support Qi Respiration.")
        
        region = self.avatar.tile.region
        
        # Nếu đang ở vùng tu luyện, kiểm tra quyền sở hữu động phủ
        if isinstance(region, CultivateRegion):
            if region.host_avatar is not None and region.host_avatar != self.avatar:
                return False, t("This cave dwelling has been occupied by {name}, cannot respire",
                               name=region.host_avatar.name)
        
        return True, ""

    def start(self) -> Event:
        # Tính toán giảm thời gian thổ nạp
        reduction = float(self.avatar.effects.get("respire_duration_reduction", 0.0))
        reduction = max(0.0, min(0.9, reduction))
        
        # Thiết lập động thời gian thực tế (duration) cho lần thổ nạp này
        base_duration = self.__class__.duration_months
        actual_duration = max(1, round(base_duration * (1.0 - reduction)))
        self.duration_months = actual_duration
        
        matched_density = self._get_matched_essence_density()
        region = self.avatar.tile.region
        
        if matched_density > 0:
            efficiency = t("excellent progress")
        elif isinstance(region, CultivateRegion) and region.essence_density > 0:
            efficiency = t("slow progress (essence mismatch)")
        else:
            efficiency = t("slow progress (sparse essence)")

        content = t("{avatar} begins respiring at {location}, {efficiency}",
                   avatar=self.avatar.name, location=self.avatar.tile.location_name, efficiency=efficiency)
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id])

    async def finish(self) -> list[Event]:
        return []
