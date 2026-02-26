# 📖 Cultivation World Simulator — Tài Liệu Kỹ Thuật

> Cập nhật: 2026-02-26 | Phiên bản: main branch

---

## 1. Giới Thiệu Dự Án

**Cultivation World Simulator** là trò chơi mô phỏng thế giới tu tiên (Xianxia) mã nguồn mở, điều khiển hoàn toàn bởi AI/LLM.

### Concept cốt lõi

| Khái niệm                  | Mô tả                                                                                           |
| -------------------------- | ----------------------------------------------------------------------------------------------- |
| **Người chơi = Thiên Đạo** | Không điều khiển nhân vật — quan sát và tác động vào thế giới như một vị thần                   |
| **NPC = AI Agent**         | Mỗi NPC hoàn toàn độc lập, được điều khiển bởi LLM với bộ nhớ, tính cách, quan hệ riêng         |
| **World = Rule Engine**    | Thế giới vận hành theo hệ thống số liệu nghiêm ngặt: linh căn, cảnh giới, công pháp, thọ nguyên |
| **Story = Emergent**       | Không có kịch bản cố định — tất cả tình tiết nảy sinh từ logic thế giới                         |

### Điểm nổi bật kỹ thuật

- **Async multi-threaded AI**: LLM calls chạy concurrent để xử lý nhiều NPC cùng lúc
- **Phase-based simulation**: Mỗi "tháng" game chạy qua 18 phase tuần tự
- **Mixin architecture**: Avatar được xây dựng từ nhiều Mixin class
- **SQLite event store**: Lưu toàn bộ lịch sử sự kiện
- **WebSocket real-time**: Frontend nhận update tức thì từ backend

---

## 2. Tech Stack

### Backend (Python)

| Thư viện     | Version | Vai trò                     |
| ------------ | ------- | --------------------------- |
| **Python**   | 3.10+   | Ngôn ngữ chính              |
| **FastAPI**  | latest  | REST API + WebSocket server |
| **asyncio**  | stdlib  | Async I/O cho LLM calls     |
| **SQLite**   | stdlib  | Lưu events database         |
| **Flask**    | latest  | Map Creator tool (dev only) |
| **pytest**   | latest  | Testing framework           |
| **tiktoken** | latest  | Token counting cho LLM      |

### Frontend (TypeScript/Vue)

| Thư viện          | Version   | Vai trò                             |
| ----------------- | --------- | ----------------------------------- |
| **Vue 3**         | 3.x       | UI framework (Composition API)      |
| **TypeScript**    | ~5.9      | Type safety                         |
| **Vite**          | ^5.4      | Build tool + Dev server             |
| **Pinia**         | ^3.0      | State management                    |
| **PixiJS**        | ^8.14     | Render bản đồ 2D (WebGL/Canvas)     |
| **pixi-viewport** | ^6.0      | Camera, zoom, pan cho bản đồ        |
| **vue3-pixi**     | ^1.0 beta | Bridge Vue ↔ PixiJS                 |
| **Naive UI**      | ^2.43     | Component library (panels, dialogs) |
| **vue-i18n**      | ^9.14     | Đa ngôn ngữ (zh/en)                 |
| **VueUse**        | ^14.0     | Composables tiện ích                |
| **Vitest**        | ^2.1      | Unit testing                        |
| **MSW**           | ^2.7      | API mocking cho tests               |
| **SASS**          | ^1.94     | CSS preprocessor                    |

### Hạ tầng

|                 |                                    |
| --------------- | ---------------------------------- |
| **Docker**      | docker-compose.yml deploy cả stack |
| **PyInstaller** | Build standalone .exe (Windows)    |
| **Steam**       | Upload lên Steam qua SteamCmd      |

---

## 3. Kiến Trúc Hệ Thống

### Tổng quan luồng dữ liệu

```
┌──────────────────────────────────────────────────────────┐
│                    Browser (Vue 3)                        │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐  ┌─────────┐ │
│  │PixiJS   │  │ Pinia    │  │ Components│  │ i18n UI │ │
│  │Map View │  │ Stores   │  │ Panels    │  │ zh/en   │ │
│  └────┬────┘  └────┬─────┘  └─────┬─────┘  └─────────┘ │
│       └────────────┴──────────────┘                      │
│                    api/ (HTTP + WebSocket)                │
└──────────────────────┬───────────────────────────────────┘
                       │ HTTP REST / WebSocket
┌──────────────────────▼───────────────────────────────────┐
│               FastAPI Server (src/server/main.py)         │
│  ┌─────────────────┐  ┌──────────────────────────────┐  │
│  │ REST Endpoints  │  │ WebSocket Handler            │  │
│  │ /api/init       │  │ Push events realtime         │  │
│  │ /api/save       │  │ Receive player commands      │  │
│  │ /api/load       │  └──────────────────────────────┘  │
│  └────────┬────────┘                                     │
└───────────┼──────────────────────────────────────────────┘
            │ Calls
┌───────────▼──────────────────────────────────────────────┐
│                  Simulator (src/sim/)                     │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ simulator.py — 18 Phase Loop (per month)            │ │
│  │  1.Perception  2.LongTermGoal  3.Gathering          │ │
│  │  4.AI Decide   5.Commit        6.Execute            │ │
│  │  7.Interactions  8.Relations   9.Death              │ │
│  │  10.Birth  11.Passive  12.Nickname  13.Phenomenon   │ │
│  │  14.Prosperity  15-17.Cleanup  18.Finalize          │ │
│  └──────────────┬──────────────────────────────────────┘ │
│                 │                                         │
│  ┌──────────────▼──────────────────────────────────────┐ │
│  │            src/classes/ (Domain Objects)             │ │
│  │  Avatar | Sect | World | Actions | Items | Effects  │ │
│  └──────────────┬──────────────────────────────────────┘ │
│                 │                                         │
│  ┌──────────────▼──────────────────────────────────────┐ │
│  │           src/systems/ (Core Game Rules)             │ │
│  │  cultivation | battle | fortune | tribulation | time│ │
│  └──────────────┬──────────────────────────────────────┘ │
│                 │                                         │
│  ┌──────────────▼──────────────────────────────────────┐ │
│  │            src/utils/llm/ (LLM Client)               │ │
│  │  Gọi DeepSeek/Ollama async, handle retry, parse JSON│ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### Vòng lặp mô phỏng chi tiết (18 Phase / tháng)

```
step() được gọi mỗi "tháng" game:

Phase  1: Perception & Knowledge
         → Mỗi Avatar cập nhật known_regions theo bán kính quan sát
         → Tự động chiếm đóng CultivateRegion trống nếu chưa có nhà

Phase  2: Long-Term Objective Thinking (async)
         → Avatar nào cần cập nhật mục tiêu dài hạn → gọi LLM
         → LongTermObjective được sinh ra/cập nhật

Phase  3: Gathering Settlement
         → Kiểm tra các sự kiện tập hợp đến hạn: Đấu giá / Ẩn Domain / Dạy học
         → Chạy toàn bộ logic gathering async

Phase  4: AI Decision (async, batch concurrent)
         → Avatar không có action và không có plan → gọi llm_ai.decide()
         → LLM trả về: [(action_name, params), ...], thinking, short_term_objective
         → Nạp vào planned_actions queue

Phase  5: Commit Plans
         → Avatar không đang thực hiện action → commit next plan
         → Tạo start_event

Phase  6: Execute Actions (multi-round)
         → avatar.tick_action() cho toàn bộ living_avatars
         → Nếu action kết thúc ngay → retry round mới (tối đa config.max_action_rounds_per_turn)

Phase  7: Initial Interaction Count
         → Events có 2+ related_avatars → cập nhật relation_interaction_states

Phase  8: Relation Evolution (async)
         → Cặp avatar có interaction_count >= threshold → RelationResolver.run_batch()
         → LLM quyết định quan hệ thay đổi không (kết giao, thành kẻ thù, kết đôi...)

Phase  9: Resolve Death
         → Avatar HP <= 0 → SERIOUS_INJURY
         → Avatar age > lifespan → OLD_AGE
         → handle_death(): xử lý toàn bộ side effects (rời tông, giải phóng động phủ...)

Phase 10: Age & Birth
         → update_age() cho tất cả
         → cleanup_dead_mortals() (thường dân già chết)
         → process_awakening(): thường dân giác thức thành tu sĩ
         → process_births(): đạo lữ sinh con

Phase 11: Passive Effects (async)
         → process_elixir_expiration(): đan dược hết hạn
         → update_time_effect(): HP hồi phục theo thời gian
         → try_trigger_fortune() + try_trigger_misfortune(): kỳ ngộ/tai họa ngẫu nhiên

Phase 12: Nickname Generation (async)
         → process_avatar_nickname(): LLM tạo biệt hiệu nếu đủ điều kiện

Phase 13: Celestial Phenomenon
         → Kiểm tra thiên tượng hết thời gian → chọn thiên tượng mới ngẫu nhiên
         → Thiên tượng ảnh hưởng tỉ lệ đột phá của toàn thế giới

Phase 14: City Prosperity
         → Mỗi CityRegion +1 prosperity tự nhiên

Phase 15-16: Handle remaining interactions + 2nd degree relations
         → Mỗi năm 1 tháng (January): tính toán quan hệ bậc 2 (bạn của bạn)

Phase 17: Cleanup long-dead avatars
         → Mỗi năm 1 tháng: xóa dữ liệu nhân vật đã chết lâu khỏi bộ nhớ

Phase 18: Finalize
         → Deduplicate events → ghi vào EventManager → log → tăng month_stamp
```

---

## 4. Cấu Trúc Thư Mục Root

```
cultivation-world-simulator/
├── src/              # Backend Python — engine chính
├── web/              # Frontend Vue 3
├── static/           # Assets tĩnh: config yml, CSV data, ảnh, nhạc
├── tests/            # Test suite (74 files)
├── docs/             # Tài liệu kỹ thuật
├── tools/            # Dev tools: map creator, img gen, i18n, packaging
├── deploy/           # Cấu hình Docker/Nginx cho production
├── assets/           # Ảnh dùng trong README
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml    # pytest + coverage config
├── EN_README.md      # README tiếng Anh
└── README.md         # README tiếng Trung
```

---

## 5. Backend Python (`src/`)

### 5.1 Cấu trúc tổng thể

```
src/
├── __init__.py
├── sim/              # Simulation engine
├── classes/          # Domain objects (tất cả class game)
├── systems/          # Hệ thống game cốt lõi
├── server/           # FastAPI server
├── utils/            # Tiện ích dùng chung
├── run/              # Logger, runner
└── i18n/             # Backend i18n (zh/en)
```

---

### 5.2 `src/sim/` — Simulation Engine

```
src/sim/
├── __init__.py
├── simulator.py       # ⭐ Vòng lặp mô phỏng chính
├── avatar_init.py     # Khởi tạo Avatar khi bắt đầu game (33KB)
├── avatar_awake.py    # Logic thường dân giác thức thành tu sĩ
├── managers/
│   ├── avatar_manager.py   # Quản lý tập hợp tất cả Avatar
│   ├── event_manager.py    # Quản lý + lưu sự kiện vào SQLite
│   └── mortal_manager.py   # Quản lý thường dân (non-cultivator)
├── save/              # Logic lưu game (serialize Avatar/World → JSON)
└── load/              # Logic tải game (deserialize JSON → objects)
```

#### `simulator.py` — Trái tim của game

Class `Simulator` nhận vào `World` và expose method `step()`. Mỗi lần gọi `step()` tiến 1 tháng. Toàn bộ 18 phase đều là private methods dạng `_phase_*()`. Quan trọng nhất:

- `_phase_decide_actions()` — gọi `llm_ai.decide()` async cho avatars cần ra quyết định
- `_phase_execute_actions()` — tick từng action, hỗ trợ multi-round chain execution
- `_phase_evolve_relations()` — batch resolve quan hệ khi đủ interaction count
- `_finalize_step()` — deduplicate events, ghi EventManager, tăng time

#### `avatar_manager.py`

Quản lý toàn bộ living/dead avatars:

- `add_avatar()`, `get_avatar(id)`, `get_living_avatars()`
- `get_avatars_in_same_region()`, `get_observable_avatars()`
- `cleanup_long_dead_avatars()` — xóa dead avatars sau N năm

#### `event_manager.py`

Quản lý sự kiện, lưu vào SQLite:

- `add_event(event)` — ghi vào DB
- `get_events_by_avatar(avatar_id)`, `get_recent_events(n)`
- `create_with_db(path)` — factory tạo EventManager với SQLite backend

---

### 5.3 `src/classes/` — Domain Objects

File lớn nhất trong project với 127 file trải qua 8 thư mục con và nhiều file ngang hàng.

#### `src/classes/core/` — Object cốt lõi

```
core/
├── avatar/            # ⭐ Class Avatar (NPC chính)
│   ├── core.py        # Avatar dataclass chính (~541 dòng)
│   ├── action_mixin.py    # Mixin: xử lý action queue và execution
│   ├── inventory_mixin.py # Mixin: túi đồ, mua/bán items
│   └── info_presenter.py  # Xuất thông tin Avatar ra dict/str cho LLM
├── world.py           # ⭐ World dataclass — toàn bộ game state
├── sect.py            # Tông môn: thành viên, kỹ thuật, phong cách, cấp bậc
└── orthodoxy.py       # Đạo thống: chính/tà phân loại, ảnh hưởng hành vi
```

##### `Avatar` Class (core.py)

Avatar là `@dataclass` kết hợp nhiều Mixin:

```python
class Avatar(AvatarSaveMixin, AvatarLoadMixin, EffectsMixin, InventoryMixin, ActionMixin):
```

Các thuộc tính chính:

| Nhóm          | Thuộc tính                                                                                     |
| ------------- | ---------------------------------------------------------------------------------------------- |
| **Định danh** | `id`, `name`, `gender`, `birth_month_stamp`                                                    |
| **Vị trí**    | `pos_x`, `pos_y`, `tile`, `known_regions`                                                      |
| **Tu luyện**  | `cultivation_progress`, `root` (linh căn), `technique`                                         |
| **Sinh tồn**  | `age`, `hp`, `alignment`, `personas`, `appearance`                                             |
| **Trang bị**  | `weapon`, `auxiliary`, `spirit_animal`, `magic_stone`, `materials`, `elixirs`                  |
| **Xã hội**    | `sect`, `sect_rank`, `relations`, `computed_relations`                                         |
| **AI**        | `thinking`, `short_term_objective`, `long_term_objective`, `planned_actions`, `current_action` |
| **Meta**      | `is_dead`, `death_info`, `nickname`, `emotion`, `metrics_history`                              |

Quan hệ semantic methods: `acknowledge_master()`, `become_lovers_with()`, `make_enemy_of()`, v.v.

##### `World` Class (world.py)

```python
@dataclass
class World:
    map: Map                        # Bản đồ tiles và regions
    month_stamp: MonthStamp         # Thời gian hiện tại
    avatar_manager: AvatarManager   # Quản lý tất cả Avatar
    mortal_manager: MortalManager   # Quản lý thường dân
    event_manager: EventManager     # Sự kiện + SQLite
    current_phenomenon: CelestialPhenomenon  # Thiên tượng hiện tại
    circulation: CirculationManager # Lưu thông vật phẩm
    gathering_manager: GatheringManager  # Sự kiện tập hợp
    history: History                # Lịch sử thế giới
    start_year: int
```

Factory `World.create_with_db()` tạo World với SQLite event storage.

##### `Sect` Class (sect.py, ~15KB)

- Attributes: `id`, `name`, `alignment`, `style`, `tier`, `orthodoxy_id`, `members`, `techniques`
- Hỗ trợ đặc biệt cho Hợp Hoan Tông (song tu), Bách Thú Tông (thuần thú)
- `add_member()`, `remove_member()`, `promote_member()`
- `get_leader()`, `get_elders()`, `get_members_by_realm()`

---

#### `src/classes/action/` — Action System

37 file, mỗi file 1 action. Cơ chế:

```
Action lifecycle:
  Avatar.planned_actions (queue)
    → commit_next_plan() → current_action (ActionInstance)
    → tick_action() mỗi tháng
    → action.is_done() → kết thúc, clear current_action
```

**Base class mô hình:**

- `action.py` — `Action` abstract base: `get_action_name()`, `start()`, `tick()`, `is_done()`
- `registry.py` — `ACTION_REGISTRY: dict[str, Type[Action]]` đăng ký tất cả actions
- `action_runtime.py` — `ActionPlan`, `ActionInstance` — wrapper cho action trong queue
- `cooldown.py` — `ActionCooldown` — ghi nhớ cooldown theo action type
- `targeting_mixin.py` — Helper tìm target avatar/region

**Nhóm Di chuyển:**

| File                       | Action             | Mô tả                            |
| -------------------------- | ------------------ | -------------------------------- |
| `move.py`                  | Move               | Di chuyển 1 bước ngẫu nhiên      |
| `move_to_avatar.py`        | MoveToAvatar       | Đi đến gần 1 Avatar cụ thể       |
| `move_away_from_avatar.py` | MoveAwayFromAvatar | Chạy trốn khỏi Avatar            |
| `move_to_region.py`        | MoveToRegion       | Đến 1 khu vực (theo pathfinding) |
| `move_away_from_region.py` | MoveAwayFromRegion | Rời khỏi khu vực                 |
| `move_to_direction.py`     | MoveToDirection    | Di chuyển theo hướng cụ thể      |

**Nhóm Tu Luyện:**

| File              | Action       | Mô tả                                |
| ----------------- | ------------ | ------------------------------------ |
| `respire.py`      | Respire      | Hấp thụ linh khí để tích lũy tu vi   |
| `meditate.py`     | Meditate     | Thiền định, hiệu quả cao hơn respire |
| `breakthrough.py` | Breakthrough | Đột phá cảnh giới (tốn nhiều tháng)  |
| `retreat.py`      | Retreat      | Bế quan — hiệu quả nhất nhưng cô lập |
| `temper.py`       | Temper       | Tôi luyện thể xác                    |
| `cast.py`         | Cast         | Thi triển công pháp (attack/buff)    |

**Nhóm Chiến Đấu:**

| File             | Action      | Mô tả                                 |
| ---------------- | ----------- | ------------------------------------- |
| `attack.py`      | Attack      | Tấn công Avatar                       |
| `assassinate.py` | Assassinate | Ám sát — cao hơn attack, ẩn hành tung |
| `escape.py`      | Escape      | Bỏ chạy khỏi nguy hiểm                |
| `self_heal.py`   | SelfHeal    | Tự hồi phục HP                        |

**Nhóm Kinh Tế & Crafting:**

| File                | Action        | Mô tả                            |
| ------------------- | ------------- | -------------------------------- |
| `buy.py`            | Buy           | Mua đồ trong CityRegion          |
| `sell.py`           | Sell          | Bán đồ trong CityRegion          |
| `refine.py`         | Refine        | Luyện đan (linh thảo → đan dược) |
| `nurture_weapon.py` | NurtureWeapon | Rèn/nâng cấp vũ khí              |
| `harvest.py`        | Harvest       | Thu hoạch linh thảo, khoáng vật  |
| `mine.py`           | Mine          | Khai thác khoáng thạch           |
| `hunt.py`           | Hunt          | Săn bắt thú vật lấy nguyên liệu  |
| `catch.py`          | Catch         | Bắt thú làm linh thú             |

**Nhóm Xã Hội:**

| File                | Action        | Mô tả                                |
| ------------------- | ------------- | ------------------------------------ |
| `educate.py`        | Educate       | Truyền công pháp/kiến thức cho đệ tử |
| `play.py`           | Play          | Thư giãn, tăng breakthrough rate     |
| `help_people.py`    | HelpPeople    | Giúp đỡ thường dân, tăng hảo cảm     |
| `devour_people.py`  | DevourPeople  | Hút tinh khí thường dân (tà đạo)     |
| `plunder_people.py` | PlunderPeople | Cướp đoạt thường dân                 |

---

#### `src/classes/mutual_action/` — Hành Động Song Phương

12 file — một Avatar khởi xướng, một Avatar phản hồi:

| File                  | Hành động       | Mô tả                               |
| --------------------- | --------------- | ----------------------------------- |
| `mutual_action.py`    | Base            | Framework xử lý initiator/responder |
| `conversation.py`     | Conversation    | Đối thoại LLM-driven giữa 2 Avatar  |
| `talk.py`             | Talk            | Nói chuyện đơn giản (quick)         |
| `gift.py`             | Gift            | Tặng quà (~11KB, nhiều logic)       |
| `impart.py`           | Impart          | Truyền thụ công pháp/bí thuật       |
| `dual_cultivation.py` | DualCultivation | Song tu (nâng cao linh lực cả 2)    |
| `spar.py`             | Spar            | Cắt luyện (luyện đấu không LLM)     |
| `attack.py`           | MutualAttack    | Chiến đấu thực sự                   |
| `drive_away.py`       | DriveAway       | Xua đuổi khỏi khu vực               |
| `occupy.py`           | Occupy          | Chiếm đoạt vật phẩm/lãnh thổ        |
| `play.py`             | MutualPlay      | Vui chơi cùng nhau                  |

---

#### `src/classes/gathering/` — Sự Kiện Tập Hợp Lớn

4 loại sự kiện có nhiều người tham gia:

| File               | Sự kiện          | Mô tả                                                              |
| ------------------ | ---------------- | ------------------------------------------------------------------ |
| `gathering.py`     | GatheringManager | Quản lý lịch và trigger gatherings                                 |
| `auction.py`       | Auction          | **Đấu giá** (~18KB): Avatar trong phạm vi đấu giá vật phẩm cao cấp |
| `hidden_domain.py` | HiddenDomain     | **Khám phá Ẩn Domain** (~15KB): nhóm chạy dungeon                  |
| `sect_teaching.py` | SectTeaching     | **Dạy học Tông môn** (~8KB): trưởng lão dạy đệ tử                  |

---

#### `src/classes/effect/` — Hệ Thống Buff/Debuff

5 file implement hệ thống effect:

- `EffectsMixin` — abstract mixin được kế thừa vào Avatar
- `recalc_effects()` — tính lại toàn bộ stats sau khi có thay đổi buff/debuff
- Effects nguồn: đan dược, thiên tượng, công pháp, tông môn style

---

#### `src/classes/items/` — Vật Phẩm

8 file:

| File             | Class                  | Mô tả                                    |
| ---------------- | ---------------------- | ---------------------------------------- |
| `elixir.py`      | Elixir, ConsumedElixir | Đan dược: tăng stats, kéo dài thọ nguyên |
| `weapon.py`      | Weapon                 | Vũ khí: tăng chiến lực                   |
| `auxiliary.py`   | Auxiliary              | Pháp bảo phụ: tăng tu tốc hay phòng thủ  |
| `magic_stone.py` | MagicStone             | Linh thạch (currency)                    |

---

#### `src/classes/environment/` — Bản Đồ & Khu Vực

7 file:

| File             | Class                                                         | Mô tả                                             |
| ---------------- | ------------------------------------------------------------- | ------------------------------------------------- |
| `map.py`         | Map                                                           | Bản đồ 70×50 tiles, chứa dict regions             |
| `tile.py`        | Tile                                                          | Ô tile cơ bản: terrain type, position, region ref |
| `region.py`      | Region, NormalRegion, SectRegion, CultivateRegion, CityRegion | 4 loại khu vực                                    |
| `sect_region.py` | SectRegion                                                    | Căn cứ tông môn                                   |
| `lode.py`        | Lode                                                          | Khoáng mạch trong khu vực                         |
| `plant.py`       | Plant                                                         | Thực vật/linh thảo có thể thu hoạch               |

**Loại Region:**

- `NormalRegion` — địa hình tự nhiên (plain, forest, mountain...)
- `SectRegion` — trụ sở tông môn, có bonus tu tốc cho thành viên
- `CultivateRegion` — Động phủ/Thánh địa tu luyện — có `host_avatar`
- `CityRegion` — Thành phố: có shop, prosperity level, thường dân

---

#### Các file classes quan trọng khác

| File                      | Class                      | Mô tả                                                                      |
| ------------------------- | -------------------------- | -------------------------------------------------------------------------- |
| `ai.py`                   | `llm_ai`                   | Singleton kết nối LLM với game. `decide()` nhận list Avatar → action plans |
| `technique.py`            | Technique                  | Công pháp tu luyện (~12KB): loại, cấp, hiệu quả, yêu cầu linh căn          |
| `history.py`              | History                    | Lịch sử và memory của thế giới/nhân vật (~10KB)                            |
| `event.py`                | Event                      | Sự kiện: timestamp, mô tả, related_avatars, id                             |
| `event_storage.py`        | EventStorage               | Lưu trữ sự kiện trong SQLite (~21KB)                                       |
| `long_term_objective.py`  | LongTermObjective          | Mục tiêu dài hạn LLM-generated                                             |
| `persona.py`              | Persona                    | Tính cách nhân vật (~5KB): các trait và compatibility                      |
| `circulation.py`          | CirculationManager         | Quản lý lưu thông vật phẩm giữa các khu vực                                |
| `story_teller.py`         | StoryTeller                | Sinh vi kịch bản (micro-theater) qua LLM (~7KB)                            |
| `single_choice.py`        | SingleChoice               | Quyết định 1 lần: LLM chọn khi có milestone (~8KB)                         |
| `nickname.py`             |                            | Sinh biệt hiệu LLM-based khi đủ điều kiện                                  |
| `celestial_phenomenon.py` | CelestialPhenomenon        | Thiên tượng ảnh hưởng cả thế giới                                          |
| `age.py`                  | Age                        | Tuổi tác + thọ nguyên theo cảnh giới                                       |
| `hp.py`                   | HP                         | Hệ thống máu, `HP_MAX_BY_REALM`                                            |
| `root.py`                 | Root                       | Linh căn (Kim/Mộc/Thủy/Hỏa/Thổ, Thiên linh, v.v.)                          |
| `alignment.py`            | Alignment                  | Chính/Tà/Trung                                                             |
| `rarity.py`               | Rarity                     | Độ hiếm items                                                              |
| `prices.py`               |                            | Hệ thống giá cả kinh tế (~4KB)                                             |
| `sect_ranks.py`           | SectRank                   | Cấp bậc trong tông môn; auto-promote khi đột phá                           |
| `relation/`               | Relation, RelationResolver | Hệ thống quan hệ + LLM resolution                                          |
| `birth.py`                |                            | Logic sinh con cho đạo lữ                                                  |
| `mortal.py`               | Mortal                     | Thường dân — không tu luyện, có dân số                                     |
| `kill_and_grab.py`        |                            | Xử lý drop đồ khi giết Avatar                                              |
| `observe.py`              |                            | Tính bán kính quan sát theo cảnh giới                                      |
| `appearance.py`           | Appearance                 | Ngoại hình nhân vật                                                        |
| `spirit_animal.py`        | SpiritAnimal               | Linh thú đồng hành                                                         |
| `emotions.py`             | EmotionType                | Trạng thái cảm xúc: CALM, ANGRY, SAD...                                    |
| `gender.py`               | Gender                     | MALE / FEMALE                                                              |
| `material.py`             | Material                   | Nguyên liệu đặc biệt                                                       |
| `animal.py`               | Animal                     | Thú vật trong thế giới                                                     |
| `avatar_metrics.py`       | AvatarMetrics              | Snapshot stats theo thời gian                                              |

---

### 5.4 `src/systems/` — Core Game Systems

6 file điều phối các quy tắc gameplay cốt lõi:

#### `cultivation.py` (~12KB) — Hệ Thống Tu Luyện

```python
class Realm(Enum):  # Cảnh giới
    MORTAL = 0
    QI_REFINING = 1  # Luyện Khí
    FOUNDATION = 2   # Trúc Cơ
    GOLDEN_CORE = 3  # Kim Đan
    NASCENT_SOUL = 4 # Nguyên Anh
    SOUL_FORMATION = 5  # Hóa Thần
    VOID_REFINING = 6   # Luyện Hư
    VOID_MERGING = 7    # Hợp Thể
    MAHAYANA = 8        # Đại Thừa
    TRIBULATION = 9     # Độ Kiếp
```

- `CultivationProgress`: `level` (0-900), `progress` (0-100), `realm` (tính từ level)
- Logic tăng tu vi theo linh căn, công pháp, thời gian
- Điều kiện đột phá breakthrough

#### `battle.py` (~12KB) — Hệ Thống Chiến Đấu

- Tính `win_rate(attacker, defender)` theo realm, linh căn, vũ khí, kỹ thuật
- Hệ thống khắc chế (Kim khắc Mộc, v.v.)
- Phong cách chiến đấu (orthodox, rogue, sect-specific)
- Kết quả: WIN/LOSE/DRAW + tổn thương HP

#### `fortune.py` (~25KB) — Kỳ Ngộ & Tai Họa

File lớn nhất trong systems. Chứa:

- `try_trigger_fortune(avatar)` — xác suất kỳ ngộ theo cảnh giới, alignment
- `try_trigger_misfortune(avatar)` — xác suất tai họa (thiên kiếp, ám toán...)
- Danh sách các loại kỳ ngộ và tai họa cụ thể
- Mỗi kỳ ngộ/tai họa dùng LLM thêm detail nếu đặc biệt

#### `tribulation.py` (~7KB) — Thiên Kiếp

- Trigger khi đột phá cảnh giới cao (Nguyên Anh trở lên)
- Tính xác suất vượt kiếp theo realm, kỹ thuật, alignment
- Hậu quả thất bại: giảm cultivation hoặc tử vong

#### `time.py` — Hệ Thống Thời Gian

```python
class MonthStamp(int):  # = year * 12 + month
class Month(IntEnum):   # JANUARY=1 ... DECEMBER=12
class Year(int)
```

Toàn bộ thời gian trong game dùng MonthStamp (int). Tính year/month từ stamp.

---

### 5.5 `src/utils/` — Tiện Ích

15 file + 1 thư mục con:

| File/Dir            | Mô tả                                                        |
| ------------------- | ------------------------------------------------------------ |
| `config.py`         | Đọc `static/local_config.yml` → `CONFIG` object toàn cục     |
| `llm/`              | **LLM client**: wrapper async cho DeepSeek/Ollama/OpenAI API |
| `name_generator.py` | Sinh tên ngẫu nhiên theo văn hóa Trung (~6KB)                |
| `resolution.py`     | Tính toán win/lose probability với randomness                |
| `normalize.py`      | Normalize data khi load từ CSV/JSON                          |
| `df.py`             | Đọc CSV game configs → `game_configs` dict                   |
| `text_wrap.py`      | Format text cho LLM prompts                                  |
| `params.py`         | Parse params từ action plan JSON                             |
| `distance.py`       | Tính Manhattan distance giữa 2 tiles                         |
| `born_region.py`    | Chọn khu vực sinh cho Avatar mới                             |
| `id_generator.py`   | Generate unique ID                                           |
| `gather.py`         | Gather logic (thu hoạch tài nguyên)                          |
| `asyncio_utils.py`  | Helpers cho async/await                                      |
| `strings.py`        | String utilities                                             |
| `io.py`             | File I/O helpers                                             |

#### `src/utils/llm/`

```
llm/
├── __init__.py    # export call_llm(), call_llm_json()
├── client.py      # HTTP client gọi LLM API (retry, timeout)
├── models.py      # Cấu hình model names (flash/pro cho từng task)
├── cache.py       # Optional response cache
├── parser.py      # Parse JSON response từ LLM
└── errors.py      # LLM-specific exceptions
```

Hỗ trợ nhiều provider qua config: DeepSeek, Ollama, bất kỳ OpenAI-compatible API nào.

---

### 5.6 `src/server/main.py` — API Server (~72KB)

FastAPI application khổng lồ — single file chứa toàn bộ server logic:

**REST Endpoints chính:**
| Endpoint | Method | Mô tả |
|---|---|---|
| `/api/init` | GET | Trạng thái khởi tạo, config info |
| `/api/world` | GET | Lấy world state JSON |
| `/api/avatar/{id}` | GET | Chi tiết 1 avatar |
| `/api/events` | GET | Danh sách sự kiện (paged) |
| `/api/save` | POST | Lưu game → JSON file |
| `/api/load` | POST | Tải game từ file |
| `/api/settings` | GET/POST | Đọc/ghi LLM config |
| `/api/start` | POST | Bắt đầu simulation mới |

**WebSocket `/ws`:**

- Server push events khi simulation chạy
- Client gửi commands: pause/resume, set avatar objective, chọn nhân vật
- Real-time feed cho event log

**Dev mode** (`--dev` flag):

- Tự động khởi động Vite dev server song song
- Auto-open browser

---

### 5.7 `src/i18n/` — Backend Internationalization

2 file:

- `__init__.py` — export hàm `t(key, **kwargs)` dùng khắp backend
- Template strings cho zh/en — phân nhánh theo `CONFIG.language`

---

## 6. Frontend Vue 3 (`web/`)

### 6.1 Cấu trúc

```
web/
├── index.html          # HTML entry point
├── package.json        # Dependencies
├── vite.config.ts      # Vite + proxy config (forward /api → :8002)
├── vitest.config.ts    # Test config
├── tsconfig.json
└── src/
    ├── main.ts         # App entry: khởi tạo Vue, Pinia, i18n, plugins
    ├── App.vue         # Root component (~9KB): layout chính
    ├── style.css       # Global styles
    ├── env.d.ts
    ├── components/     # UI components
    ├── stores/         # Pinia state
    ├── api/            # HTTP + WebSocket client
    ├── composables/    # Reusable Vue composition functions
    ├── locales/        # i18n translation files
    ├── types/          # TypeScript interfaces
    ├── utils/          # Frontend utilities
    ├── constants/      # Constants
    ├── directives/     # Vue custom directives
    └── __tests__/      # 22 test files
```

---

### 6.2 `web/src/components/`

```
components/
├── LoadingOverlay.vue   # Màn hình loading toàn trang (progress bar, tips)
├── SplashLayer.vue      # Màn hình giới thiệu/splash screen
├── SystemMenu.vue       # Top menu: Save/Load/Settings (~17KB)
├── game/                # 24 components game chính
└── layout/              # 2 layout wrappers
```

**`game/` components (24 files):**

| Component           | Mô tả                                        |
| ------------------- | -------------------------------------------- |
| `GameMap.vue`       | Bản đồ chính dùng PixiJS (~viewport + tiles) |
| `AvatarPanel.vue`   | Panel chi tiết nhân vật được chọn            |
| `AvatarList.vue`    | Danh sách tất cả Avatar                      |
| `EventLog.vue`      | Feed sự kiện game realtime                   |
| `SectPanel.vue`     | Thông tin tông môn                           |
| `RegionPanel.vue`   | Thông tin khu vực being viewed               |
| `WorldPanel.vue`    | Thông tin tổng quan thế giới                 |
| `SettingsPanel.vue` | Cài đặt LLM provider, speed                  |
| `TimeControl.vue`   | Điều khiển tốc độ simulation                 |
| `AvatarCard.vue`    | Card nhỏ preview nhân vật                    |
| ...                 | (và nhiều sub-components khác)               |

---

### 6.3 `web/src/stores/` — Pinia State Management

8 stores, mỗi store quản lý 1 domain:

| Store       | File         | State chính                               | Actions                         |
| ----------- | ------------ | ----------------------------------------- | ------------------------------- |
| **World**   | `world.ts`   | avatars, sects, regions, time, phenomenon | fetchWorld, updateFromSocket    |
| **Avatar**  | `avatar.ts`  | selectedAvatar, avatarDetail              | selectAvatar, fetchAvatarDetail |
| **Event**   | `event.ts`   | events[], filters, pagination             | addEvent, fetchEvents           |
| **Map**     | `map.ts`     | selectedTile, viewport state              | selectTile, setViewport         |
| **Setting** | `setting.ts` | llmConfig, simSpeed, language             | saveSetting, loadSetting        |
| **Socket**  | `socket.ts`  | isConnected, lastMessage                  | connect, disconnect             |
| **System**  | `system.ts`  | isLoading, error, gameState               | setLoading, handleError         |
| **UI**      | `ui.ts`      | openPanels, modals, layout                | togglePanel, openModal          |

---

### 6.4 `web/src/api/` — API Layer

```
api/
├── http.ts        # Axios instance với base URL + interceptors
├── index.ts       # Re-export all modules
├── socket.ts      # WebSocket client: connect, send, onMessage
└── modules/       # 5 API modules theo domain
    ├── world.ts       # GET /api/world
    ├── avatar.ts      # GET /api/avatar/:id
    ├── events.ts      # GET /api/events
    ├── settings.ts    # GET/POST /api/settings
    └── game.ts        # POST /api/start, /api/save, /api/load
```

**WebSocket flow:**

```
socket.ts connect() → ws://localhost:8002/ws
  → server push: { type: "events", data: [...] }
  → socket store onMessage() → event store addEvents()
  → EventLog.vue re-render
```

---

### 6.5 `web/src/locales/` — Frontend i18n

4 file dịch:

- `zh.json` — Tiếng Trung (bản gốc)
- `en.json` — Tiếng Anh
- (+ 2 file utility/type)

Sử dụng `vue-i18n`, switch language qua Setting store.

---

## 7. Static Files (`static/`)

```
static/
├── local_config.yml     # ⭐ File cấu hình chính
├── game_configs/        # CSV data cho world
│   ├── sect.csv             # Danh sách tông môn
│   ├── technique.csv        # Danh sách công pháp
│   ├── normal_region.csv    # Khu vực địa hình
│   ├── sect_region.csv      # Khu vực tông môn
│   ├── cultivate_region.csv # Khu vực tu luyện
│   ├── city_region.csv      # Thành phố
│   ├── weapon.csv           # Vũ khí
│   ├── auxiliary.csv        # Pháp bảo
│   ├── elixir.csv           # Đan dược
│   ├── world_info.csv       # World lore text
│   └── tile_map.csv / region_map.csv  # Bản đồ 70×50
├── bgm/                 # Background music
└── images/              # Game images
```

**`local_config.yml`** — File quan trọng nhất cho người dùng:

```yaml
llm:
  provider: deepseek # hoặc ollama, openai
  api_key: "sk-..."
  model: deepseek-chat
server:
  host: "127.0.0.1"
  port: 8002
game:
  npc_count: 50
  npc_awakening_rate_per_month: 0.02
  sim_speed: 1.0
language: zh # zh hoặc en
```

---

## 8. Tests (`tests/`)

**74 file test** với pytest, asyncio_mode="auto". Cấu trúc theo domain:

### Nhóm unit tests

| File                         | Kiểm tra                                 |
| ---------------------------- | ---------------------------------------- |
| `test_battle.py`             | Battle system win rate, khắc chế         |
| `test_cultivation_logic.py`  | Tính toán realm, breakthrough conditions |
| `test_circulation.py`        | Circulation manager logic                |
| `test_elixir.py`             | Đan dược: consume, expire, stack         |
| `test_relations_logic.py`    | Set/get/clear relations                  |
| `test_breakthrough_logic.py` | Điều kiện đột phá                        |
| `test_death.py`              | Xử lý death events                       |
| `test_birth.py`              | Sinh con logic                           |
| `test_age_death_mechanic.py` | Tuổi tác và thọ nguyên                   |
| `test_prices.py`             | Hệ thống giá                             |
| `test_cooldown.py`           | Action cooldown                          |
| `test_equipment.py`          | Trang bị                                 |
| `test_mortal.py`             | Thường dân                               |

### Nhóm action tests

| File                     | Mô tả                     |
| ------------------------ | ------------------------- |
| `test_action_combat.py`  | attack, escape, self_heal |
| `test_action_craft.py`   | refine, nurture_weapon    |
| `test_action_social.py`  | educate, gift, talk       |
| `test_action_move.py`    | move actions              |
| `test_action_respire.py` | Hấp thụ linh khí          |
| `test_action_retreat.py` | Bế quan                   |
| `test_action_play.py`    | Thư giãn                  |
| `test_mutual_actions.py` | Song phương (~25KB)       |
| `test_auction.py`        | Đấu giá (~14KB)           |
| `test_hidden_domain.py`  | Ẩn domain exploration     |

### Nhóm integration tests

| File                            | Mô tả                                              |
| ------------------------------- | -------------------------------------------------- |
| `test_game_init_integration.py` | Khởi tạo game end-to-end (**38KB**, test lớn nhất) |
| `test_ai.py`                    | AI decision making với LLM mock (**24KB**)         |
| `test_llm_failures.py`          | Xử lý LLM errors, retries (**25KB**)               |
| `test_save_load_events.py`      | Save/Load + event persistence                      |
| `test_save_load_death.py`       | Save/Load với dead avatars                         |

### Nhóm API tests

| File                         | Mô tả                      |
| ---------------------------- | -------------------------- |
| `test_api_events.py`         | REST API events endpoints  |
| `test_websocket_handlers.py` | WebSocket handlers (~19KB) |
| `test_server_binding.py`     | Server startup và binding  |
| `test_init_status_api.py`    | Init status API (~19KB)    |

### Cấu hình test

```python
# conftest.py (10KB) — fixtures dùng chung
@pytest.fixture
def world():        # World với fakemap
def avatar():       # Avatar mẫu
def living_world(): # World với nhiều avatars
```

---

## 9. Tools (`tools/`)

### 9.1 `extract/` — Trích xuất lore từ tiểu thuyết

- **`extract.py`** — Đọc file .txt tiểu thuyết tu tiên, dùng LLM phân tích chunks async (5 concurrent), extract tông môn → lưu `res.csv`
- **`clean.py`** — Làm sạch và deduplicate kết quả
- Dùng cho: nhập lore từ truyện yêu thích để dùng làm nền tảng thế giới

**Chạy:** `python tools/extract/extract.py path/to/novel.txt [--test]`

---

### 9.2 `i18n/` — Công cụ đa ngôn ngữ

| File                     | Mô tả                                  |
| ------------------------ | -------------------------------------- |
| `extract_csv.py`         | Trích chuỗi cần dịch từ CSV game data  |
| `build_mo.py`            | Compile `.po` → `.mo` (gettext format) |
| `split_po.py`            | Tách file `.po` lớn                    |
| `check_po_duplicates.py` | Phát hiện bản dịch trùng               |
| `translate.py`           | LLM auto-translate                     |
| `translate_name.py`      | Dịch tên địa điểm, nhân vật            |

---

### 9.3 `img_gen/` — Sinh ảnh nhân vật & tông môn

Dùng **Alibaba DashScope (Qwen Image Plus)**:

- **`gen_img.py`** — Script chính, 32+ prompt nhân vật nam/nữ, 5+ prompt tông môn
- **`process_img.py`** — Post-process: resize, crop tách sprite
- **`tile_prompts.py`** — Prompt bank cho tile địa hình

---

### 9.4 `img_gemini/` — Xử lý ảnh với Gemini Vision

- **`split.py`** / **`split2.py`** — Tách sprite sheet thành tiles lẻ
- **`split_cloud.py`** — Tách cloud textures

---

### 9.5 `map_creator/` — Trình tạo bản đồ

Flask web app cho phép **vẽ bản đồ thế giới** bằng giao diện kéo thả:

- Grid 70×50 tiles
- Panel trái: danh sách tiles + regions (đọc từ CSV)
- Click tile → chọn terrain type
- Click region → assign region ID vào tile
- **Save** → xuất `tile_map.csv` và `region_map.csv` trực tiếp dùng trong game

**Chạy:** `python tools/map_creator/main.py` → `http://127.0.0.1:5000`

---

### 9.6 `package/` — Build & Release

PowerShell pipeline cho Windows:

| File                     | Bước                               |
| ------------------------ | ---------------------------------- |
| `pack.ps1`               | Build EXE với PyInstaller          |
| `compress.ps1`           | Nén thành .zip                     |
| `release.ps1`            | Quy trình release hoàn chỉnh       |
| `upload_steam.ps1`       | Deploy lên Steam                   |
| `hook-tiktoken.py`       | PyInstaller runtime hook           |
| `runtime_hook_setcwd.py` | Fix working directory khi chạy EXE |

---

### 9.7 `migrate_assets_and_map.py` & `process_assets.py`

- **`migrate_assets_and_map.py`** — Batch rename/move assets khi refactor cấu trúc
- **`process_assets.py`** — Batch resize/optimize ảnh trong `assets/`

---

## 10. Docs (`docs/`)

| File                 | Nội dung                                         |
| -------------------- | ------------------------------------------------ |
| `frontend.md`        | Architecture frontend: Vue 3, components, stores |
| `i18n-guide.md`      | Hướng dẫn thêm ngôn ngữ mới                      |
| `sound.md`           | Hệ thống âm thanh/BGM                            |
| `testing.md`         | Quy tắc viết test, cách chạy                     |
| `vue_performance.md` | Tối ưu hiệu năng Vue                             |
| `glossary.csv`       | Bảng thuật ngữ zh/en (~38KB)                     |
| `specs/`             | Thư mục spec chi tiết các tính năng              |

---

## 11. Quick Start

```bash
# Cách 1: Docker (production-like)
docker-compose up -d --build
# Frontend: http://localhost:8123
# Backend:  http://localhost:8002

# Cách 2: Source code (development)
pip install -r requirements.txt
cd web && npm install && cd ..
python src/server/main.py --dev
# Auto-opens http://localhost:5173

# Test
pytest                          # Tất cả tests
pytest tests/test_battle.py    # Test cụ thể
pytest --cov=src               # Coverage report
```

**Bước đầu tiên sau khi chạy:**
Vào **Settings** → chọn LLM provider → nhập API key → lưu → Start simulation.

---

## 12. Quan Hệ Giữa Các Module

```
                    World
                  /   |   \
           Avatar  Sect  Map
          /  |  \    |    |
    Action Items Effect  Region──Tile
      |                   |
   MutualAction      SectRegion
      |                   |
   Gathering        CultivateRegion
                         |
    systems/cultivation  CityRegion
    systems/battle
    systems/fortune
         |
    utils/llm ──────────────── AI
         |                      |
    (DeepSeek/Ollama)      classes/ai.py
                                |
                          decide() → ActionPlan[]
```

---

_Tài liệu này được tạo từ phân tích trực tiếp source code tại `d:\DEV\Project\cultivation-world-simulator`_
