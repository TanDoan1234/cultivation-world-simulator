from __future__ import annotations

import random
from src.i18n import t
from src.classes.action import TimedAction
from src.classes.action.cooldown import cooldown_action
from src.classes.event import Event
from src.systems.cultivation import Realm
from src.classes.story_teller import StoryTeller
from src.systems.tribulation import TribulationSelector
from src.classes.hp import HP_MAX_BY_REALM
from src.classes.effect import _merge_effects

# —— Cấu hình: Những "Cảnh giới xuất phát" nào sẽ tạo ra cốt truyện đột phá (biến toàn cục) ——
ALLOW_STORY_FROM_REALMS: list[Realm] = [
    Realm.Foundation_Establishment,  # Trúc Cơ
    Realm.Core_Formation,            # Kim Đan
]


@cooldown_action
class Breakthrough(TimedAction):
    """
    Đột phá cảnh giới.
    Tỷ lệ thành công được quyết định bởi `CultivationProgress.get_breakthrough_success_rate()`;
    Khi thất bại sẽ giảm Thọ nguyên (năm) theo `CultivationProgress.get_breakthrough_fail_reduce_lifespan()`.
    """
    
    # ID Đa ngôn ngữ
    ACTION_NAME_ID = "breakthrough_action_name"
    DESC_ID = "breakthrough_description"
    REQUIREMENTS_ID = "breakthrough_requirements"
    
    # Các hằng số không cần dịch
    EMOJI = "⚡"
    PARAMS = {}
    # Hồi chiêu: Đột phá nên có CD (thời gian hồi), tránh việc spam liên tục
    ACTION_CD_MONTHS: int = 3
    # Đột phá là đại sự (ghi nhớ dài hạn)
    IS_MAJOR: bool = True
    # Giữ lại các khai báo hằng số cấp lớp, thực tế đọc cấu hình cấp module

    def calc_success_rate(self) -> float:
        """
        Tính toán tỷ lệ thành công khi đột phá cảnh giới (dựa trên tiến độ tu vi)
        """
        base = self.avatar.cultivation_progress.get_breakthrough_success_rate()
        # Đọc thêm điểm thưởng từ avatar.effects (đã hợp nhất từ căn cốt/công pháp/tông môn...)
        bonus = float(self.avatar.effects.get("extra_breakthrough_success_rate", 0.0))
        # Giới hạn trong khoảng [0, 1]
        return max(0.0, min(1.0, base + bonus))

    duration_months = 1

    def _execute(self) -> None:
        """
        Thực hiện đột phá cảnh giới
        """
        assert self.avatar.cultivation_progress.can_break_through()
        success_rate = self.calc_success_rate()
        # Ghi lại thông tin cơ bản của lần thử này
        self._success_rate_cached = success_rate
        if random.random() < success_rate:
            old_realm = self.avatar.cultivation_progress.realm
            self.avatar.cultivation_progress.break_through()
            new_realm = self.avatar.cultivation_progress.realm

            # Cập nhật HP tối đa khi đột phá thành công
            if new_realm != old_realm:
                self._update_hp_on_breakthrough(new_realm)
                # Thành công: Đảm bảo thọ nguyên tối đa ít nhất đạt mức cơ bản của cảnh giới mới
                self.avatar.age.ensure_max_lifespan_at_least_realm_base(new_realm)
            # Ghi lại kết quả để dùng cho sự kiện finish
            self._last_result = (
                "success",
                old_realm.value,
                new_realm.value,
            )
        else:
            # Đột phá thất bại: Giảm giới hạn thọ nguyên tối đa
            reduce_years = self.avatar.cultivation_progress.get_breakthrough_fail_reduce_lifespan()
            self.avatar.age.decrease_max_lifespan(reduce_years)
            # Ghi lại kết quả để dùng cho sự kiện finish
            self._last_result = ("fail", int(reduce_years))

    def _update_hp_on_breakthrough(self, new_realm):
        """
        Cập nhật HP tối đa và hồi phục hoàn toàn khi đột phá cảnh giới thành công

        Args:
            new_realm: Cảnh giới mới
        """
        new_max_hp = HP_MAX_BY_REALM.get(new_realm, 100)

        # Tính toán lượng HP tăng thêm
        hp_increase = new_max_hp - self.avatar.hp.max

        # Cập nhật giá trị tối đa và hồi phục lượng HP tương ứng
        self.avatar.hp.add_max(hp_increase)
        self.avatar.hp.recover(hp_increase)  # Hồi phục hoàn toàn HP khi đột phá

    def can_start(self) -> tuple[bool, str]:
        ok = self.avatar.cultivation_progress.can_break_through()
        return (ok, "" if ok else t("Not at bottleneck, cannot breakthrough"))

    def start(self) -> Event:
        # Khởi tạo trạng thái
        self._last_result = None
        self._success_rate_cached = None
        # Dự đoán xem có tạo cốt truyện và lựa chọn kiếp nạn hay không
        old_realm = self.avatar.cultivation_progress.realm
        self._gen_story = old_realm in ALLOW_STORY_FROM_REALMS
        if self._gen_story:
            self._calamity = TribulationSelector.choose_tribulation(self.avatar)
            self._calamity_other = TribulationSelector.choose_related_avatar(self.avatar, self._calamity)
        else:
            self._calamity = None
            self._calamity_other = None
        content = t("{avatar} begins attempting breakthrough", avatar=self.avatar.name)
        return Event(self.world.month_stamp, content, related_avatars=[self.avatar.id], is_major=True)

    # TimedAction đã thống nhất logic step

    async def finish(self) -> list[Event]:
        if not self._last_result:
            return []
        result_ok = self._last_result[0] == "success"
        if not self._gen_story:
            # Không tạo cốt truyện: Không xuất hiện kiếp nạn, chỉ hiển thị kết quả đơn giản
            result_text = t("Breakthrough succeeded") if result_ok else t("Breakthrough failed")
            core_text = t("{avatar} breakthrough result: {result}", 
                         avatar=self.avatar.name, result=result_text)
            return [Event(self.world.month_stamp, core_text, related_avatars=[self.avatar.id], is_major=True)]

        calamity = self._calamity
        result_text = t("succeeded") if result_ok else t("failed")
        core_text = t("{avatar} encountered {calamity} tribulation, breakthrough {result}",
                     avatar=self.avatar.name, calamity=calamity, result=result_text)
        rel_ids = [self.avatar.id]
        if self._calamity_other is not None:
            try:
                rel_ids.append(self._calamity_other.id)
            except Exception:
                pass
        events: list[Event] = [Event(self.world.month_stamp, core_text, related_avatars=rel_ids, is_major=True)]

        # Người tham gia cốt truyện: Bản thân + (tùy chọn) nhân vật liên quan
        prompt = TribulationSelector.get_story_prompt(str(calamity))
        # Đột phá ở chế độ bắt buộc đơn nhân, không thay đổi quan hệ (vì không có tương tác như song tu/chiến đấu)
        story_result = t("Breakthrough succeeded") if result_ok else t("Breakthrough failed")
        story = await StoryTeller.tell_story(core_text, story_result, self.avatar, self._calamity_other, prompt=prompt, allow_relation_changes=False)
        events.append(Event(self.world.month_stamp, story, related_avatars=rel_ids, is_story=True))
        return events
