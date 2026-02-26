"""
Lớp cốt lõi Avatar (Nhân vật)

Lớp Avatar đã được tinh giản, kết hợp các chức năng hoàn chỉnh thông qua Mixin.
"""
import random
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.classes.sect_ranks import SectRank
    from src.classes.environment.region import CultivateRegion
    from src.classes.core.orthodoxy import Orthodoxy

from src.systems.time import MonthStamp
from src.classes.core.world import World
from src.sim.save.avatar_save_mixin import AvatarSaveMixin
from src.sim.load.avatar_load_mixin import AvatarLoadMixin
from src.classes.environment.tile import Tile
from src.classes.environment.region import Region
from src.systems.cultivation import CultivationProgress
from src.classes.root import Root
from src.classes.technique import Technique, get_technique_by_sect
from src.classes.age import Age
from src.classes.event import Event
from src.classes.action_runtime import ActionPlan, ActionInstance
from src.classes.alignment import Alignment
from src.classes.persona import Persona, get_random_compatible_personas
from src.classes.material import Material
from src.classes.items.weapon import Weapon
from src.classes.items.auxiliary import Auxiliary
from src.classes.items.magic_stone import MagicStone
from src.classes.hp import HP, HP_MAX_BY_REALM
from src.classes.relation.relation import Relation
from src.classes.core.sect import Sect
from src.classes.appearance import Appearance, get_random_appearance
from src.classes.spirit_animal import SpiritAnimal
from src.classes.long_term_objective import LongTermObjective
from src.classes.nickname_data import Nickname
from src.classes.emotions import EmotionType
from src.utils.config import CONFIG
from src.classes.items.elixir import ConsumedElixir, Elixir
from src.classes.avatar_metrics import AvatarMetrics
from src.classes.mortal import Mortal
from src.classes.gender import Gender

# Import các Mixin
from src.classes.effect import EffectsMixin
from src.classes.core.avatar.inventory_mixin import InventoryMixin
from src.classes.core.avatar.action_mixin import ActionMixin

persona_num = CONFIG.avatar.persona_num


@dataclass
class Avatar(
    AvatarSaveMixin,
    AvatarLoadMixin,
    EffectsMixin,
    InventoryMixin,
    ActionMixin,
):
    """
    Lớp dành cho NPC (Nhân vật).
    Chứa toàn bộ thông tin về nhân vật đó.
    """
    world: World
    name: str
    id: str
    birth_month_stamp: MonthStamp
    age: Age
    gender: Gender
    cultivation_progress: CultivationProgress = field(default_factory=lambda: CultivationProgress(0))
    pos_x: int = 0
    pos_y: int = 0
    tile: Optional[Tile] = None

    root: Root = field(default_factory=lambda: random.choice(list(Root)))
    personas: List[Persona] = field(default=None)  # type: ignore
    technique: Technique | None = None
    _pending_events: List[Event] = field(default_factory=list)
    current_action: Optional[ActionInstance] = None
    planned_actions: List[ActionPlan] = field(default_factory=list)
    thinking: str = ""
    short_term_objective: str = ""
    long_term_objective: Optional[LongTermObjective] = None
    magic_stone: MagicStone = field(default_factory=lambda: MagicStone(0))
    materials: dict[Material, int] = field(default_factory=dict)
    hp: HP = field(default_factory=lambda: HP(0, 0))
    relations: dict["Avatar", Relation] = field(default_factory=dict)
    # Cache quan hệ bậc hai (được tính toán định kỳ bởi Simulator để tối ưu tính toán Giao tế)
    computed_relations: dict["Avatar", Relation] = field(default_factory=dict)
    alignment: Alignment | None = None
    sect: Sect | None = None
    sect_rank: "SectRank | None" = None
    appearance: Appearance = field(default_factory=get_random_appearance)
    weapon: Optional[Weapon] = None
    weapon_proficiency: float = 0.0
    auxiliary: Optional[Auxiliary] = None
    spirit_animal: Optional[SpiritAnimal] = None
    nickname: Optional[Nickname] = None
    emotion: EmotionType = EmotionType.CALM
    custom_pic_id: Optional[int] = None
    
    elixirs: List[ConsumedElixir] = field(default_factory=list)
    # Danh sách hiệu ứng tạm thời: [{"source": str, "effects": dict, "start_month": int, "duration": int}]
    temporary_effects: List[dict] = field(default_factory=list)

    is_dead: bool = False
    death_info: Optional[dict] = None

    _new_action_set_this_step: bool = False
    _action_cd_last_months: dict[str, int] = field(default_factory=dict)
    
    # Danh sách các khu vực đã thông hiểu (Known Regions)
    known_regions: set[int] = field(default_factory=set)

    # Lưu trữ lịch sử Căn cơ (Metrics history) qua từng tháng
    metrics_history: List[AvatarMetrics] = field(default_factory=list)
    enable_metrics_tracking: bool = False
    max_metrics_history: int = 1200  # Tối đa 100 năm

    # Bộ đếm tương tác quan hệ: key=target_id, value={"count": 0, "checked_times": 0}
    relation_interaction_states: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {"count": 0, "checked_times": 0}))

    # [Bổ sung] Danh sách con cái (Thường dân)
    children: List["Mortal"] = field(default_factory=list)

    # [Bổ sung] ID khu vực sinh ra
    born_region_id: Optional[int] = None

    # [Bổ sung] Cache thời gian bắt đầu quan hệ
    # Key: ID Avatar đối phương, Value: MonthStamp lúc bắt đầu (int)
    relation_start_dates: dict[str, int] = field(default_factory=dict)

    # Danh sách các động phủ (vùng tu luyện) sở hữu (không tham gia tuần tự hóa, được tái thiết qua load_game)
    owned_regions: List["CultivateRegion"] = field(default_factory=list, init=False)

    def occupy_region(self, region: "CultivateRegion") -> None:
        """
        Chiếm giữ một động phủ, xử lý liên kết hai chiều và dọn dẹp chủ cũ.
        """
        # Nếu đã là của mình thì không cần thao tác
        if region.host_avatar == self:
            if region not in self.owned_regions:
                self.owned_regions.append(region)
            return

        # Nếu có chủ cũ, yêu cầu chủ cũ giải phóng
        if region.host_avatar is not None:
            region.host_avatar.release_region(region)

        # Thiết lập quan hệ mới
        region.host_avatar = self
        if region not in self.owned_regions:
            self.owned_regions.append(region)

    def release_region(self, region: "CultivateRegion") -> None:
        """
        Từ bỏ quyền sở hữu một động phủ.
        """
        if region in self.owned_regions:
            self.owned_regions.remove(region)
        
        # Chỉ xóa chủ khi chủ của region thực sự là bản thân (tránh xóa nhầm chủ mới)
        if region.host_avatar == self:
            region.host_avatar = None

    def add_breakthrough_rate(self, rate: float, duration: int = 1) -> None:
        """
        Tăng tỷ lệ đột phá thành công (hiệu ứng tạm thời)
        """
        self.temporary_effects.append({
            "source": "play_benefit",
            "effects": {"extra_breakthrough_success_rate": rate},
            "start_month": int(self.world.month_stamp),
            "duration": duration
        })
        self.recalc_effects()

    # ========== Liên quan đến Đan dược / Tông môn ==========

    def consume_elixir(self, elixir: Elixir) -> bool:
        """
        Phục dụng đan dược
        :return: Có phục dụng thành công hay không
        """
        # 1. Kiểm tra cảnh giới: Chỉ có thể phục dụng đan dược có cảnh giới bằng hoặc thấp hơn hiện tại
        if elixir.realm > self.cultivation_progress.realm:
            return False
            
        # 2. Kiểm tra phục dụng lặp lại: Nếu đã phục dụng loại đan dược cùng loại chưa hết hiệu lực thì không có tác dụng
        # Vì đan dược diên thọ là vĩnh viễn, nên mỗi loại đan dược diên thọ chỉ có thể phục dụng một lần.
        for consumed in self.elixirs:
            if consumed.elixir.id == elixir.id:
                if not consumed.is_completely_expired(int(self.world.month_stamp)):
                    return False

        # 3. Ghi lại trạng thái phục dụng
        self.elixirs.append(ConsumedElixir(elixir, int(self.world.month_stamp)))
        
        # 4. Kích hoạt tính toán lại thuộc tính ngay lập tức (vì có thể có thay đổi chỉ số tức thì, hoặc thay đổi MaxHP/Thọ nguyên)
        self.recalc_effects()
        
        return True
    
    def process_elixir_expiration(self, current_month: int) -> None:
        """
        Xử lý đan dược hết hạn:
        1. Loại bỏ các đan dược đã hết hạn hoàn toàn
        2. Nếu có loại bỏ, kích hoạt tính toán lại thuộc tính
        """
        need_recalc = False
        
        # Xử lý đan dược
        if self.elixirs:
            original_count = len(self.elixirs)
            self.elixirs = [
                e for e in self.elixirs 
                if not e.is_completely_expired(current_month)
            ]
            if len(self.elixirs) < original_count:
                need_recalc = True

        # Xử lý hiệu ứng tạm thời
        if self.temporary_effects:
            original_temp_count = len(self.temporary_effects)
            self.temporary_effects = [
                eff for eff in self.temporary_effects
                if current_month < (eff.get("start_month", 0) + eff.get("duration", 0))
            ]
            if len(self.temporary_effects) < original_temp_count:
                need_recalc = True
        
        # Nếu có hết hạn, tính toán lại thuộc tính
        if need_recalc:
            self.recalc_effects()

    def join_sect(self, sect: Sect, rank: "SectRank") -> None:
        """Gia nhập tông môn"""
        if self.is_dead:
            return
        if self.sect:
            self.leave_sect()
        self.sect = sect
        self.sect_rank = rank
        sect.add_member(self)
        
    def leave_sect(self) -> None:
        """Rời khỏi tông môn"""
        if self.sect:
            self.sect.remove_member(self)
            self.sect = None
            self.sect_rank = None

    def get_sect_str(self) -> str:
        """Lấy tên hiển thị tông môn: Nếu có tông môn trả về "Tên tông môn + Chức vụ", nếu không trả về "Tán tu"."""
        from src.i18n import t
        if self.sect is None:
            return t("Rogue Cultivator")
        if self.sect_rank is None:
            return self.sect.name
        from src.classes.sect_ranks import get_rank_display_name
        rank_name = get_rank_display_name(self.sect_rank, self.sect)
        return t("{sect} {rank}", sect=self.sect.name, rank=rank_name)

    def get_sect_rank_name(self) -> str:
        """Lấy tên hiển thị của chức vụ trong tông môn"""
        from src.i18n import t
        if self.sect is None or self.sect_rank is None:
            return t("Rogue Cultivator")
        from src.classes.sect_ranks import get_rank_display_name
        return get_rank_display_name(self.sect_rank, self.sect)

    # ========== Liên quan đến Tử vong ==========

    def set_dead(self, reason: str, time: MonthStamp) -> None:
        """Thiết lập trạng thái tử vong cho nhân vật."""
        if self.is_dead:
            return
            
        self.is_dead = True
        self.death_info = {
            "time": int(time),
            "reason": reason,
            "location": (self.pos_x, self.pos_y)
        }
        
        self.planned_actions.clear()
        self.current_action = None
        self._pending_events.clear()
        self.thinking = ""
        self.short_term_objective = ""
        
        # Giải phóng toàn bộ động phủ sở hữu
        # Sao chép danh sách để duyệt vì release_region sẽ sửa đổi danh sách gốc
        for region in list(self.owned_regions):
            self.release_region(region)

        if self.sect:
            self.sect.remove_member(self)

    def death_by_old_age(self) -> bool:
        """Kiểm tra xem có chết vì lão hóa (hết thọ nguyên) không"""
        return self.age.death_by_old_age(self.cultivation_progress.realm)

    # ========== Theo dõi trạng thái (Metrics) ==========

    def record_metrics(self, tags: Optional[List[str]] = None) -> Optional[AvatarMetrics]:
        """
        Ghi lại bản sao Căn cơ (Metrics) hiện tại.

        Args:
            tags: Các nhãn sự kiện tùy chọn

        Returns:
            Bản ghi trạng thái đã tạo, hoặc None nếu tính năng theo dõi chưa được bật
        """
        if not self.enable_metrics_tracking:
            return None

        metrics = AvatarMetrics(
            timestamp=self.world.month_stamp,
            age=self.age.value,
            cultivation_level=self.cultivation_progress.level,
            cultivation_progress=self.cultivation_progress.progress,
            hp=self.hp.value,
            hp_max=self.hp.max_value,
            spirit_stones=self.magic_stone.amount,
            relations_count=len(self.relations),
            known_regions_count=len(self.known_regions),
            tags=tags or [],
        )

        self.metrics_history.append(metrics)

        # Tự động dọn dẹp bản ghi cũ
        if len(self.metrics_history) > self.max_metrics_history:
            self.metrics_history = self.metrics_history[-self.max_metrics_history:]

        return metrics

    def get_metrics_summary(self) -> dict:
        """Lấy tóm tắt biến động Căn cơ"""
        if not self.metrics_history:
            return {"enabled": self.enable_metrics_tracking, "count": 0}

        return {
            "enabled": self.enable_metrics_tracking,
            "count": len(self.metrics_history),
            "first_record": self.metrics_history[0].timestamp,
            "latest_record": self.metrics_history[-1].timestamp,
            "cultivation_growth": (
                self.metrics_history[-1].cultivation_level -
                self.metrics_history[0].cultivation_level
            ),
        }

    # ========== Tuổi tác và Tu vi ==========

    def update_age(self, current_month_stamp: MonthStamp):
        """Cập nhật tuổi tác"""
        self.age.update_age(current_month_stamp, self.birth_month_stamp)

    def update_cultivation(self, new_level: int):
        """Cập nhật tiến độ tu tiên, cập nhật thọ nguyên và chức vụ tông môn khi tăng cảnh giới"""
        old_realm = self.cultivation_progress.realm
        self.cultivation_progress.level = new_level
        self.cultivation_progress.realm = self.cultivation_progress.get_realm(new_level)
        
        if self.cultivation_progress.realm != old_realm:
            self.age.update_realm(self.cultivation_progress.realm)
            self.recalc_effects()
            from src.classes.sect_ranks import check_and_promote_sect_rank
            check_and_promote_sect_rank(self, old_realm, self.cultivation_progress.realm)

    # ========== Khu vực và Vị trí ==========

    def _init_known_regions(self):
        """Khởi tạo các khu vực đã biết: Vị trí hiện tại + Trụ sở tông môn"""
        if self.tile and self.tile.region:
            self.known_regions.add(self.tile.region.id)
        
        if self.sect:
            for r in self.world.map.sect_regions.values():
                if r.sect_id == self.sect.id:
                    self.known_regions.add(r.id)
                    break

    # ========== Liên quan đến Quan hệ ==========

    def set_relation(self, other: "Avatar", relation: Relation) -> None:
        """Thiết lập quan hệ với một nhân vật khác."""
        from src.classes.relation.relations import set_relation
        set_relation(self, other, relation)

    # ========== Các thao tác quan hệ ngữ nghĩa (Semantic Relation Operations) ==========

    def acknowledge_master(self, teacher: "Avatar") -> None:
        """
        [Bản thân] bái [teacher] làm sư phụ.
        Ngữ nghĩa: Xác lập đối phương là MASTER (Sư phụ) của tôi.
        """
        self.set_relation(teacher, Relation.IS_MASTER_OF)

    def accept_disciple(self, student: "Avatar") -> None:
        """
        [Bản thân] nhận [student] làm đồ đệ.
        Ngữ nghĩa: Xác lập đối phương là DISCIPLE (Đồ đệ) của tôi.
        """
        self.set_relation(student, Relation.IS_DISCIPLE_OF)

    def acknowledge_parent(self, parent: "Avatar") -> None:
        """
        [Bản thân] nhận [parent] làm phụ mẫu (cha/mẹ).
        Ngữ nghĩa: Xác lập đối phương là PARENT (Cha mẹ) của tôi.
        """
        self.set_relation(parent, Relation.IS_PARENT_OF)
        
    def acknowledge_child(self, child: "Avatar") -> None:
        """
        [Bản thân] nhận [child] làm tử nữ (con cái).
        Ngữ nghĩa: Xác lập đối phương là CHILD (Con cái) của tôi.
        """
        self.set_relation(child, Relation.IS_CHILD_OF)

    def become_lovers_with(self, other: "Avatar") -> None:
        """
        [Bản thân] cùng [other] kết thành đạo lữ.
        """
        self.set_relation(other, Relation.IS_LOVER_OF)

    def make_friend_with(self, other: "Avatar") -> None:
        """
        [Bản thân] cùng [other] kết thành hảo hữu (bạn bè).
        """
        self.set_relation(other, Relation.IS_FRIEND_OF)

    def make_enemy_of(self, other: "Avatar") -> None:
        """
        [Bản thân] xem [other] là cừu địch (kẻ thù).
        """
        self.set_relation(other, Relation.IS_ENEMY_OF)

    def get_relation(self, other: "Avatar") -> Optional[Relation]:
        """Lấy quan hệ với một nhân vật khác."""
        from src.classes.relation.relations import get_relation
        return get_relation(self, other)

    def clear_relation(self, other: "Avatar") -> None:
        """Xóa bỏ quan hệ với một nhân vật khác."""
        from src.classes.relation.relations import clear_relation
        clear_relation(self, other)

    # ========== Hiển thị thông tin (Ủy thác) ==========

    def get_info(self, detailed: bool = False) -> dict:
        from src.classes.core.avatar.info_presenter import get_avatar_info
        return get_avatar_info(self, detailed)

    def get_structured_info(self) -> dict:
        from src.classes.core.avatar.info_presenter import get_avatar_structured_info
        return get_avatar_structured_info(self)

    def get_expanded_info(
        self, 
        co_region_avatars: Optional[List["Avatar"]] = None,
        other_avatar: Optional["Avatar"] = None,
        detailed: bool = False
    ) -> dict:
        from src.classes.core.avatar.info_presenter import get_avatar_expanded_info
        return get_avatar_expanded_info(self, co_region_avatars, other_avatar, detailed)

    def get_other_avatar_info(self, other_avatar: "Avatar") -> str:
        from src.classes.core.avatar.info_presenter import get_other_avatar_info
        return get_other_avatar_info(self, other_avatar)

    def get_desc(self, detailed: bool = False) -> str:
        """Lấy mô tả văn bản của nhân vật (bao gồm chi tiết hiệu ứng)"""
        from src.classes.core.avatar.info_presenter import get_avatar_desc
        return get_avatar_desc(self, detailed=detailed)

    # ========== Các phương thức Magic ==========

    @property
    def orthodoxy(self) -> "Orthodoxy | None":
        """Lấy đạo thống của nhân vật (Nếu có tông môn thì theo tông môn, nếu không thì là tán tu)"""
        from src.classes.core.orthodoxy import get_orthodoxy
        
        # Ưu tiên trả về đạo thống của tông môn
        if self.sect:
            return get_orthodoxy(self.sect.orthodoxy_id)
            
        # Tán tu trả về đạo thống mặc định
        return get_orthodoxy("sanxiu")

    @property
    def current_action_name(self) -> str:
        """Lấy tên hành động hiện tại, mặc định trả về 'Đang suy nghĩ'"""
        if self.current_action and self.current_action.action:
            action = self.current_action.action
            # Sử dụng get_action_name() để lấy tên hành động đã dịch
            return action.get_action_name()
        from src.i18n import t
        return t("action_thinking")

    def __post_init__(self):
        """Tự động khởi tạo tile và HP sau khi Avatar được tạo"""
        self.tile = self.world.map.get_tile(self.pos_x, self.pos_y)
        
        max_hp = HP_MAX_BY_REALM.get(self.cultivation_progress.realm, 100)
        self.hp = HP(max_hp, max_hp)
        
        if self.personas is None:
            self.personas = get_random_compatible_personas(persona_num, avatar=self)

        if self.technique is None:
            self.technique = get_technique_by_sect(self.sect)

        if self.sect:
            self.sect.add_member(self)

        if self.alignment is None:
            if self.sect is not None:
                self.alignment = self.sect.alignment
            else:
                self.alignment = random.choice(list(Alignment))
        
        self.recalc_effects()
        self._init_known_regions()

    def __hash__(self) -> int:
        if not hasattr(self, 'id'):
            # Lập trình phòng thủ: Nếu ID chưa được khởi tạo (ví dụ trong quá trình deepcopy), sử dụng địa chỉ vùng nhớ đối tượng
            return super().__hash__()
        return hash(self.id)

    def __str__(self) -> str:
        return str(self.get_info(detailed=False))
