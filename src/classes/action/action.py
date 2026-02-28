from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from src.i18n import t
from src.classes.event import Event
from src.classes.action_runtime import ActionResult, ActionStatus
from src.utils.params import filter_kwargs_for_callable

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar
    from src.classes.core.world import World


def long_action(step_month: int):
    """
    Decorator cho hành động dài hạn, dùng để tự động thêm tính năng quản lý thời gian cho lớp hành động.

    Args:
        step_month: Số tháng cần thiết để hoàn thành hành động.
    """
    def decorator(cls):
        # Thiết lập thuộc tính lớp để lớp cơ sở sử dụng
        cls._step_month = step_month

        def is_finished(self, *args, **kwargs) -> bool:
            """
            Dựa trên chênh lệch thời gian để xác định hành động đã hoàn thành chưa.
            Chấp nhận nhưng bỏ qua các tham số bổ sung để duy trì tính tương thích với các loại hành động khác.
            """
            if self.start_monthstamp is None:
                return False
            # Logic sửa đổi: Sử dụng >= step_month - 1 thay vì >= step_month
            # Như vậy hành động 1 tháng sẽ hoàn thành ngay trong tháng đầu tiên (chênh lệch 0 >= 0),
            # hành động 10 tháng sẽ hoàn thành ở tháng thứ 10 (chênh lệch 9 >= 9).
            # Điều này tránh được lỗi thực hiện dư một tháng như trước đây.
            return (self.world.month_stamp - self.start_monthstamp) >= self.step_month - 1

        # Chỉ thêm phương thức is_finished
        cls.is_finished = is_finished

        return cls

    return decorator


class Action(ABC):
    """
    Các hành động mà nhân vật có thể thực hiện.
    Ví dụ: di chuyển, tấn công, thu thập, xây dựng, v.v.
    """
    
    # Các biến lớp hỗ trợ đa ngôn ngữ (sẽ được lớp con ghi đè)
    ACTION_NAME_ID: str = ""
    DESC_ID: str = ""
    REQUIREMENTS_ID: str = ""

    # Có cho phép tham gia các cuộc tụ họp hay không (ví dụ: đấu giá, đại tỷ võ)
    ALLOW_GATHERING: bool = True
    
    # Có cho phép kích hoạt các sự kiện thế giới ngẫu nhiên hay không (ví dụ: kỳ ngộ, vận hạn)
    ALLOW_WORLD_EVENTS: bool = True

    def __init__(self, avatar: Avatar, world: World):
        """
        Truyền vào tham chiếu (ref) của avatar.
        Nhờ đó khi thực thi thực tế, có thể biết được năng lực và trạng thái của avatar.
        Tham số world là tùy chọn; nếu không truyền, sẽ thử lấy từ avatar.world.
        """
        self.avatar = avatar
        self.world = world

    @abstractmethod
    def execute(self) -> None:
        pass

    @property
    def name(self) -> str:
        """
        Lấy tên định danh của hành động.
        """
        return str(self.__class__.__name__)

    EMOJI: str = ""
    
    @classmethod
    def get_action_name(cls) -> str:
        """Lấy tên hành động đã được dịch"""
        if cls.ACTION_NAME_ID:
            return t(cls.ACTION_NAME_ID)
        return cls.__name__
    
    @classmethod
    def get_desc(cls) -> str:
        """Lấy mô tả hành động đã được dịch"""
        if cls.DESC_ID:
            return t(cls.DESC_ID)
        return ""
    
    @classmethod
    def get_requirements(cls) -> str:
        """Lấy điều kiện thực hiện đã được dịch"""
        if cls.REQUIREMENTS_ID:
            return t(cls.REQUIREMENTS_ID)
        return ""

    def get_save_data(self) -> dict:
        """Lấy dữ liệu runtime cần lưu trữ vào bản lưu (save gam)"""
        return {}

    def load_save_data(self, data: dict) -> None:
        """Tải dữ liệu runtime từ bản lưu"""
        pass


class DefineAction(Action):
    def __init__(self, avatar: Avatar, world: World):
        """
        Khởi tạo hành động, xử lý thiết lập các thuộc tính cho hành động dài hạn.
        """
        super().__init__(avatar, world)

        # Nếu là hành động dài hạn, khởi tạo các thuộc tính liên quan
        if hasattr(self.__class__, '_step_month'):
            self.step_month = self.__class__._step_month
            self.start_monthstamp = None

    def execute(self, *args, **kwargs) -> None:
        """
        Thực thi hành động, xử lý logic quản lý thời gian, sau đó gọi triển khai cụ thể của _execute.
        """
        # Nếu là hành động dài hạn và thực hiện lần đầu, ghi lại thời điểm bắt đầu
        if hasattr(self, 'step_month') and self.start_monthstamp is None:
            self.start_monthstamp = self.world.month_stamp

        self._execute(*args, **kwargs)

    @abstractmethod
    def _execute(self, *args, **kwargs) -> None:
        """
        Logic thực thi hành động cụ thể, do lớp con triển khai.
        """
        pass

    def get_save_data(self) -> dict:
        data = super().get_save_data()
        # Nhiều hành động dài hạn (bao gồm cả MoveToDirection) đều thiết lập thuộc tính này
        if hasattr(self, 'start_monthstamp'):
            val = self.start_monthstamp
            data['start_monthstamp'] = int(val) if val is not None else None
        return data

    def load_save_data(self, data: dict) -> None:
        super().load_save_data(data)
        if 'start_monthstamp' in data:
            val = data['start_monthstamp']
            if val is not None:
                from src.systems.time import MonthStamp
                self.start_monthstamp = MonthStamp(val)
            else:
                self.start_monthstamp = None


class LLMAction(Action):
    """
    Hành động dựa trên LLM, loại hành động này thường không cần định nghĩa quy tắc thực tế.
    Thay vào đó là một định nghĩa trừu tượng, chỉ có hệ quả ở cấp độ xã hội.
    Ví dụ: "Sỉ nhục", "Nhìn chằm chằm đầy hung ác", "Hủy hôn", v.v.
    Loại hành động này sẽ được tạo ra và thực thi thông qua LLM, khiến NPC ghi nhớ và tạo ra hệ quả về sau,
    nhưng không cần phía quy tắc (Rule engine) phải phản hồi trực tiếp.
    """

    pass


class ChunkActionMixin():
    """
    Mảnh hành động (Action Chunk), có thể hiểu là một phần nhỏ được cắt ra từ một hành động.
    Avatar không thể trực tiếp thực hiện mảnh hành động này, mà nó trở thành một bước trong quá trình thực hiện một hành động nào đó của avatar.
    """

    pass


class ActualActionMixin():
    """
    Hành động thực tế có thể được gọi bởi Quy tắc/LLM để avatar thực thi.
    Không nhất thiết phải gồm nhiều bước (step), cũng có thể chỉ có duy nhất một bước.

    Giao diện mới: Lớp con bắt buộc phải triển khai can_start/start/step/finish.
    
    Biến lớp:
    - IS_MAJOR: Có phải là đại sự (ghi nhớ dài hạn) hay không, mặc định là False (tiểu sự/ghi nhớ ngắn hạn).
    """
    
    # Mặc định là tiểu sự (ghi nhớ ngắn hạn)
    IS_MAJOR: bool = False

    def create_event(self, content: str, related_avatars=None) -> Event:
        """
        Phương thức hỗ trợ tạo sự kiện, tự động mang theo thuộc tính is_major.
        
        Args:
            content: Nội dung sự kiện.
            related_avatars: Danh sách ID các nhân vật liên quan.
            
        Returns:
            Đối tượng Event, với is_major được thiết lập dựa theo biến lớp IS_MAJOR của Action hiện tại.
        """
        from src.classes.action.action import Action
        # Lấy thuộc tính IS_MAJOR của lớp hiện tại
        is_major = self.__class__.IS_MAJOR if hasattr(self.__class__, 'IS_MAJOR') else False
        return Event(
            month_stamp=self.world.month_stamp,
            content=content,
            related_avatars=related_avatars,
            is_major=is_major
        )

    @abstractmethod
    def can_start(self, **params) -> tuple[bool, str]:
        return True, ""

    @abstractmethod
    def start(self, **params) -> Event | None:
        return None

    @abstractmethod
    def step(self, **params) -> ActionResult:
        ...

    @abstractmethod
    async def finish(self, **params) -> list[Event]:
        return []


class InstantAction(DefineAction, ActualActionMixin):
    """
    Hành động tức thời: Hoàn thành ngay trong một lần step. Lớp con chỉ cần triển khai _execute.
    """

    def step(self, **params) -> ActionResult:
        params_for_execute = filter_kwargs_for_callable(self._execute, params)
        self._execute(**params_for_execute)
        return ActionResult(status=ActionStatus.COMPLETED, events=[])


class TimedAction(DefineAction, ActualActionMixin):
    """
    Hành động dài hạn: Kiểm soát thời gian duy trì thông qua thuộc tính lớp duration_months.
    Lớp con triển khai _execute như là logic thực thi hàng tháng.
    """

    duration_months: int = 1

    def step(self, **params) -> ActionResult:
        if not hasattr(self, 'start_monthstamp') or self.start_monthstamp is None:
            self.start_monthstamp = self.world.month_stamp
        params_for_execute = filter_kwargs_for_callable(self._execute, params)
        self._execute(**params_for_execute)
        done = (self.world.month_stamp - self.start_monthstamp) >= (self.duration_months - 1)
        return ActionResult(status=(ActionStatus.COMPLETED if done else ActionStatus.RUNNING), events=[])
