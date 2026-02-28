from enum import Enum
from functools import total_ordering

from src.classes.color import Color

@total_ordering
class Realm(Enum):
    Qi_Refinement = "QI_REFINEMENT"           # Luyện Khí
    Foundation_Establishment = "FOUNDATION_ESTABLISHMENT"  # Trúc Cơ
    Core_Formation = "CORE_FORMATION"        # Kim Đan
    Nascent_Soul = "NASCENT_SOUL"            # Nguyên Anh

    def __str__(self) -> str:
        """Trả về tên hiển thị đã dịch của Cảnh giới"""
        from src.i18n import t
        return t(realm_msg_ids.get(self, self.value))

    @staticmethod
    def from_str(s: str) -> "Realm":
        s = str(s).strip().replace(" ", "_").upper()
        # Thiết lập ánh xạ để tương thích với nhiều định dạng đầu vào khác nhau
        mapping = {
            "练气": "QI_REFINEMENT", "QI_REFINEMENT": "QI_REFINEMENT", "QI REFINEMENT": "QI_REFINEMENT", "LUYỆN_KHÍ": "QI_REFINEMENT",
            "筑基": "FOUNDATION_ESTABLISHMENT", "FOUNDATION_ESTABLISHMENT": "FOUNDATION_ESTABLISHMENT", "FOUNDATION ESTABLISHMENT": "FOUNDATION_ESTABLISHMENT", "TRÚC_CƠ": "FOUNDATION_ESTABLISHMENT",
            "金丹": "CORE_FORMATION", "CORE_FORMATION": "CORE_FORMATION", "CORE FORMATION": "CORE_FORMATION", "KIM_ĐAN": "CORE_FORMATION",
            "元婴": "NASCENT_SOUL", "NASCENT_SOUL": "NASCENT_SOUL", "NASCENT SOUL": "NASCENT_SOUL", "NGUYÊN_ANH": "NASCENT_SOUL"
        }
        realm_id = mapping.get(s, "QI_REFINEMENT")
        return Realm(realm_id)

    @property
    def color_rgb(self) -> tuple[int, int, int]:
        """Trả về giá trị màu RGB tương ứng với Cảnh giới"""
        color_map = {
            Realm.Qi_Refinement: Color.COMMON_WHITE,
            Realm.Foundation_Establishment: Color.UNCOMMON_GREEN,
            Realm.Core_Formation: Color.EPIC_PURPLE,
            Realm.Nascent_Soul: Color.LEGENDARY_GOLD,
        }
        return color_map.get(self, Color.COMMON_WHITE)

    @classmethod
    def from_id(cls, realm_id: int) -> "Realm":
        index = realm_id - 1
        if index < 0 or index >= len(REALM_ORDER):
            raise ValueError(f"Unknown realm_id: {realm_id}")
        return REALM_ORDER[index]

    def __lt__(self, other):
        if not isinstance(other, Realm):
            return NotImplemented
        return REALM_RANK[self] < REALM_RANK[other]

    def __le__(self, other):
        if not isinstance(other, Realm):
            return NotImplemented
        return REALM_RANK[self] <= REALM_RANK[other]

    def __gt__(self, other):
        if not isinstance(other, Realm):
            return NotImplemented
        return REALM_RANK[self] > REALM_RANK[other]

    def __ge__(self, other):
        if not isinstance(other, Realm):
            return NotImplemented
        return REALM_RANK[self] >= REALM_RANK[other]
        

@total_ordering
class Stage(Enum):
    Early_Stage = "EARLY_STAGE"    # Sơ Kỳ
    Middle_Stage = "MIDDLE_STAGE"  # Trung Kỳ
    Late_Stage = "LATE_STAGE"      # Hậu Kỳ

    def __str__(self) -> str:
        """Trả về tên hiển thị đã dịch của Giai đoạn"""
        from src.i18n import t
        return t(stage_msg_ids.get(self, self.value))

    @staticmethod
    def from_str(s: str) -> "Stage":
        s = str(s).strip().replace(" ", "_").upper()
        mapping = {
            "前期": "EARLY_STAGE", "EARLY_STAGE": "EARLY_STAGE", "EARLY STAGE": "EARLY_STAGE", "SƠ_KỲ": "EARLY_STAGE",
            "中期": "MIDDLE_STAGE", "MIDDLE_STAGE": "MIDDLE_STAGE", "MIDDLE STAGE": "MIDDLE_STAGE", "TRUNG_KỲ": "MIDDLE_STAGE",
            "后期": "LATE_STAGE", "LATE_STAGE": "LATE_STAGE", "LATE STAGE": "LATE_STAGE", "HẬU_KỲ": "LATE_STAGE"
        }
        stage_id = mapping.get(s, "EARLY_STAGE")
        return Stage(stage_id)

    def __lt__(self, other):
        if not isinstance(other, Stage):
            return NotImplemented
        return STAGE_RANK[self] < STAGE_RANK[other]

    def __le__(self, other):
        if not isinstance(other, Stage):
            return NotImplemented
        return STAGE_RANK[self] <= STAGE_RANK[other]

    def __gt__(self, other):
        if not isinstance(other, Stage):
            return NotImplemented
        return STAGE_RANK[self] > STAGE_RANK[other]

    def __ge__(self, other):
        if not isinstance(other, Stage):
            return NotImplemented
        return STAGE_RANK[self] >= STAGE_RANK[other]

# Ánh xạ msgid
realm_msg_ids = {
    Realm.Qi_Refinement: "qi_refinement",
    Realm.Foundation_Establishment: "foundation_establishment",
    Realm.Core_Formation: "core_formation",
    Realm.Nascent_Soul: "nascent_soul",
}

stage_msg_ids = {
    Stage.Early_Stage: "early_stage",
    Stage.Middle_Stage: "middle_stage",
    Stage.Late_Stage: "late_stage",
}

# Thứ tự và xếp hạng Cảnh giới thống nhất, tránh định nghĩa lặp lại
REALM_ORDER: tuple[Realm, ...] = (
    Realm.Qi_Refinement,
    Realm.Foundation_Establishment,
    Realm.Core_Formation,
    Realm.Nascent_Soul,
)
REALM_RANK: dict[Realm, int] = {realm: idx for idx, realm in enumerate(REALM_ORDER)}

# Thứ tự và xếp hạng Giai đoạn thống nhất, tránh định nghĩa lặp lại
STAGE_ORDER: tuple[Stage, ...] = (
    Stage.Early_Stage,
    Stage.Middle_Stage,
    Stage.Late_Stage,
)
STAGE_RANK: dict[Stage, int] = {stage: idx for idx, stage in enumerate(STAGE_ORDER)}

LEVELS_PER_REALM = 30
LEVELS_PER_STAGE = 10

REALM_TO_MOVE_STEP = {
    Realm.Qi_Refinement: 2,
    Realm.Foundation_Establishment: 3,
    Realm.Core_Formation: 4,
    Realm.Nascent_Soul: 5,
}

class CultivationProgress:
    """
    Tiến độ tu tiên (bao gồm cấp độ, cảnh giới và kinh nghiệm)
    Hiện tại có 4 đại cảnh giới, mỗi cảnh giới chia thành Sơ Kỳ, Trung Kỳ, Hậu Kỳ. Mỗi kỳ tương ứng 10 cấp.
    Vì vậy mỗi đại cảnh giới tương ứng với 30 cấp. Khi cấp độ của cảnh giới đã đầy, tu sĩ sẽ rơi vào bình cảnh, cần phải đột phá mới có thể tiến vào cảnh giới tiếp theo và tăng cấp.
    Cụ thể:
    Luyện Khí (Qi Refinement): Sơ Kỳ (1-10), Trung Kỳ (11-20), Hậu Kỳ (21-30), Đột phá (31)
    Trúc Cơ (Foundation Establishment): Sơ Kỳ (31-40), Trung Kỳ (41-50), Hậu Kỳ (51-60), Đột phá (61)
    Kim Đan (Core Formation): Sơ Kỳ (61-70), Trung Kỳ (71-80), Hậu Kỳ (81-90), Đột phá (91)
    Nguyên Anh (Nascent Soul): Sơ Kỳ (91-100), Trung Kỳ (101-110), Hậu Kỳ (111-120), Đột phá (121)
    """

    def __init__(self, level: int, exp: int = 0):
        self.level = level
        self.exp = exp
        self.realm = self.get_realm(level)
        self.stage = self.get_stage(level)

    def get_realm(self, level: int) -> Realm:
        """Lấy Cảnh giới (suy luận toán học, không phụ thuộc bảng ánh xạ)"""
        if level <= 0:
            return Realm.Qi_Refinement
        realm_index = (level - 1) // LEVELS_PER_REALM  # Chỉ số 0-based
        return REALM_ORDER[min(realm_index, len(REALM_ORDER) - 1)]

    def get_stage(self, level: int) -> Stage:
        """Lấy Giai đoạn (suy luận toán học: 1-10 Sơ Kỳ, 11-20 Trung Kỳ, 21-30 Hậu Kỳ)"""
        if level <= 0:
            return Stage.Early_Stage
        stage_index = ((level - 1) % LEVELS_PER_REALM) // LEVELS_PER_STAGE
        return STAGE_ORDER[min(stage_index, len(STAGE_ORDER) - 1)]

    def get_move_step(self) -> int:
        """
        Khoảng cách tối đa có thể di chuyển mỗi tháng:
        Luyện Khí: 2
        Trúc Cơ: 3
        Kim Đan: 4
        Nguyên Anh: 5
        """
        return REALM_TO_MOVE_STEP[self.realm]

    def get_detailed_info(self) -> str:
        from src.i18n import t
        can_break_through = self.can_break_through()
        can_break_through_str = t("Needs breakthrough") if can_break_through else t("Not at bottleneck, no breakthrough needed")
        return t("{realm} {stage} (Level {level}) {status}", 
                realm=str(self.realm), stage=str(self.stage), 
                level=self.level, status=can_break_through_str)

    def get_info(self) -> str:
        return f"{self.realm} {self.stage}"

    def get_exp_required(self) -> int:
        """
        Tính toán điểm kinh nghiệm cần thiết để thăng lên cấp độ tiếp theo.
        Sử dụng công thức đại số đơn giản: base_exp + (level - 1) * increment + realm_bonus
        
        Trả về:
            Kinh nghiệm cần thiết
        """
        next_level = self.level + 1
        
        base_exp = 100  # Kinh nghiệm cơ bản
        increment = 50   # Mỗi cấp tăng thêm 50 điểm kinh nghiệm
        
        # Tính toán kinh nghiệm cơ sở
        exp_required = base_exp + (next_level - 1) * increment
        
        # Thưởng cảnh giới: Tăng theo cấp bậc cảnh giới của next_level (suy luận toán học)
        realm_index = (max(1, next_level) - 1) // LEVELS_PER_REALM
        realm_bonus = realm_index * 1000
        
        return exp_required + realm_bonus

    def get_exp_progress(self) -> tuple[int, int]:
        """
        Lấy tiến độ kinh nghiệm hiện tại
        
        Trả về:
            (Kinh nghiệm hiện tại, Kinh nghiệm cần để thăng cấp)
        """
        required_exp = self.get_exp_required()
        return self.exp, required_exp

    def add_exp(self, exp_amount: int) -> bool:
        """
        Tăng điểm kinh nghiệm
        
        Tham số:
            exp_amount: Số lượng kinh nghiệm muốn thêm
        
        Trả về:
            True nếu thăng cấp, ngược lại False
        """
        self.exp += exp_amount

        leveled_up = False
        # Hỗ trợ thăng nhiều cấp cùng lúc, nhưng sẽ dừng lại ở "bình cảnh" (30/60/90…) để chờ đột phá
        while True:
            # Vị trí bình cảnh: level > 0 và level % LEVELS_PER_REALM == 0
            if self.is_in_bottleneck():
                break
            if not self.is_level_up():
                break
            required_exp = self.get_exp_required()
            self.exp -= required_exp
            self.level += 1
            self.realm = self.get_realm(self.level)
            self.stage = self.get_stage(self.level)
            leveled_up = True
            if self.is_in_bottleneck():
                break

        return leveled_up

    def break_through(self):
        """
        Đột phá cảnh giới
        """
        self.level += 1
        self.realm = self.get_realm(self.level)
        self.stage = self.get_stage(self.level)

    def is_in_bottleneck(self) -> bool:
        """
        Kiểm tra xem có đang ở trạng thái bình cảnh hay không.
        Đang ở cấp 30, 60, 90… của mỗi đại cảnh giới (level > 0 và level % LEVELS_PER_REALM == 0).
        """
        return self.level > 0 and (self.level % LEVELS_PER_REALM == 0)

    def can_break_through(self) -> bool:
        """
        Kiểm tra xem có thể đột phá hay không
        """
        # Kiểm tra giới hạn tu vi cao nhất: nếu đã đạt đỉnh của cảnh giới cuối cùng thì không thể đột phá thêm
        max_level = len(REALM_ORDER) * LEVELS_PER_REALM
        if self.level >= max_level:
            return False
        return self.is_in_bottleneck()

    def can_cultivate(self) -> bool:
        """
        Kiểm tra xem có thể tiếp tục tu luyện hay không.
        Nếu gặp bình cảnh, nghĩa là tu vi đã viên mãn, không thể tu luyện thêm mà phải đột phá trước.
        """
        return not self.is_in_bottleneck()

    def is_level_up(self) -> bool:
        """
        Kiểm tra xem kinh nghiệm hiện tại có đủ để lên cấp tiếp theo không
        """
        exp_required = self.get_exp_required()
        return self.exp >= exp_required

    def __str__(self) -> str:
        from src.i18n import t
        bottleneck_status = t("Yes") if self.is_in_bottleneck() else t("No")
        return t("{realm} {stage} (Level {level}). At bottleneck: {status}",
                realm=str(self.realm), stage=str(self.stage),
                level=self.level, status=bottleneck_status)

    def get_breakthrough_success_rate(self) -> float:
        return breakthrough_success_rate_by_realm[self.realm]
    
    def get_breakthrough_fail_reduce_lifespan(self) -> int:
        return breakthrough_fail_reduce_lifespan_by_realm[self.realm]
    
    def to_dict(self) -> dict:
        """Chuyển đổi thành dictionary có thể tuần tự hóa (serialize)"""
        return {
            "level": self.level,
            "exp": self.exp,
            "realm": self.realm.name,  # Lưu tên định danh của enum
            "stage": self.stage.name
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CultivationProgress":
        """Tái thiết CultivationProgress từ dictionary"""
        return cls(level=data["level"], exp=data["exp"])



breakthrough_success_rate_by_realm = {
    Realm.Qi_Refinement: 0.8, # Luyện Khí, 80%
    Realm.Foundation_Establishment: 0.6, # Trúc Cơ, 60%
    Realm.Core_Formation: 0.4, # Kim Đan, 40%
    Realm.Nascent_Soul: 0.2, # Nguyên Anh, 20%
}

breakthrough_fail_reduce_lifespan_by_realm = {
    Realm.Qi_Refinement: 5,
    Realm.Foundation_Establishment: 10,
    Realm.Core_Formation: 15,
    Realm.Nascent_Soul: 20,
}