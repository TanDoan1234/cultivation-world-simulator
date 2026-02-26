from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from src.classes.environment.map import Map
from src.systems.time import Year, Month, MonthStamp
from src.sim.managers.avatar_manager import AvatarManager
from src.sim.managers.mortal_manager import MortalManager
from src.sim.managers.event_manager import EventManager
from src.classes.circulation import CirculationManager
from src.classes.gathering.gathering import GatheringManager
from src.classes.history import History
from src.utils.df import game_configs
from src.classes.language import language_manager, LanguageType
from src.i18n import t

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar
    from src.classes.celestial_phenomenon import CelestialPhenomenon


@dataclass
class World():
    map: Map
    month_stamp: MonthStamp
    avatar_manager: AvatarManager = field(default_factory=AvatarManager)
    # Quản lý thường dân
    mortal_manager: MortalManager = field(default_factory=MortalManager)
    # Quản lý sự kiện toàn cục
    event_manager: EventManager = field(default_factory=EventManager)
    # Thiên địa linh cơ hiện tại (buff/debuff cấp thế giới)
    current_phenomenon: Optional["CelestialPhenomenon"] = None
    # Năm bắt đầu thiên địa linh cơ (dùng để tính toán thời gian duy trì)
    phenomenon_start_year: int = 0
    # Quản lý lưu thông vật phẩm xuất thế
    circulation: CirculationManager = field(default_factory=CirculationManager)
    # Quản lý Gathering
    gathering_manager: GatheringManager = field(default_factory=GatheringManager)
    # Lịch sử thế giới
    history: "History" = field(default_factory=lambda: History())
    # Năm bắt đầu của thế giới
    start_year: int = 0

    def get_info(self, detailed: bool = False, avatar: Optional["Avatar"] = None) -> dict:
        """
        Trả về thông tin thế giới (dict), bao gồm thông tin bản đồ (dict).
        Nếu chỉ định avatar, sẽ truyền cho map.get_info để lọc khu vực và tính toán khoảng cách.
        """
        static_info = self.static_info
        map_info = self.map.get_info(detailed=detailed, avatar=avatar)
        world_info = {**map_info, **static_info}

        if self.current_phenomenon:
            # Sử dụng translation Key
            key = t("Current World Phenomenon")
            # Định dạng nội dung, lưu ý ở đây giả định name và desc đã theo ngôn ngữ hiện tại (là thuộc tính đối tượng, xác định khi load)
            # Nhưng nếu cần định dạng cụ thể trong Prompt (như tiếng Trung dùng 【】, tiếng Anh không dùng), cũng có thể đưa vào key
            # Để đơn giản, chúng ta đưa cả định dạng vào bản dịch
            # "phenomenon_format": "【{name}】{desc}" (ZH) vs "{name}: {desc}" (EN)
            value = t("phenomenon_format", name=self.current_phenomenon.name, desc=self.current_phenomenon.desc)
            world_info[key] = value

        return world_info

    def get_avatars_in_same_region(self, avatar: "Avatar"):
        return self.avatar_manager.get_avatars_in_same_region(avatar)

    def get_observable_avatars(self, avatar: "Avatar"):
        return self.avatar_manager.get_observable_avatars(avatar)

    def set_history(self, history_text: str):
        """Thiết lập văn bản lịch sử thế giới"""
        self.history.text = history_text
        
    def record_modification(self, category: str, id_str: str, changes: dict):
        """
        Ghi lại các thay đổi (diff) lịch sử
        
        Args:
            category: Danh mục sửa đổi (sects, regions, techniques, weapons, auxiliaries)
            id_str: Chuỗi ID của đối tượng
            changes: Dictionary các thuộc tính đã sửa đổi
        """
        if category not in self.history.modifications:
            self.history.modifications[category] = {}
            
        if id_str not in self.history.modifications[category]:
            self.history.modifications[category][id_str] = {}
            
        # Cộng dồn sửa đổi (cái sau ghi đè cái trước)
        self.history.modifications[category][id_str].update(changes)

    @property
    def static_info(self) -> dict:
        info_list = game_configs.get("world_info", [])
        desc = {}
        for row in info_list:
            t_val = row.get("title")
            d_val = row.get("desc")
            if t_val and d_val:
                desc[t_val] = d_val
        
        if self.history.text:
            key = t("History")
            desc[key] = self.history.text
        return desc

    @classmethod
    def create_with_db(
        cls,
        map: "Map",
        month_stamp: MonthStamp,
        events_db_path: Path,
        start_year: int = 0,
    ) -> "World":
        """
        Factory method: Tạo thực thể World sử dụng SQLite để lưu trữ sự kiện bền vững.

        Args:
            map: Đối tượng bản đồ.
            month_stamp: Dấu thời gian.
            events_db_path: Đường dẫn tệp cơ sở dữ liệu sự kiện.
            start_year: Năm bắt đầu của thế giới.

        Returns:
            Thực thể World đã cấu hình xong.
        """
        event_manager = EventManager.create_with_db(events_db_path)
        return cls(
            map=map,
            month_stamp=month_stamp,
            event_manager=event_manager,
            start_year=start_year,
        )
