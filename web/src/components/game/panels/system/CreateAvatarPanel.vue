<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { RelationType } from "@/constants/relations";
import {
  avatarApi,
  type GameDataDTO,
  type CreateAvatarParams,
  type SimpleAvatarDTO,
} from "../../../../api";
import { useWorldStore } from "../../../../stores/world";
import {
  useMessage,
  NInput,
  NSelect,
  NSlider,
  NRadioGroup,
  NRadioButton,
  NForm,
  NFormItem,
  NButton,
} from "naive-ui";

const emit = defineEmits<{
  (e: "created"): void;
}>();

const { t } = useI18n();
const worldStore = useWorldStore();
const message = useMessage();
const loading = ref(false);

// --- State ---
const gameData = ref<GameDataDTO | null>(null);
const avatarMeta = ref<{ males: number[]; females: number[] } | null>(null);
const avatarList = ref<SimpleAvatarDTO[]>([]); // For relation selection

const createForm = ref<CreateAvatarParams>({
  surname: "",
  given_name: "",
  gender: "MALE",
  age: 16,
  level: undefined,
  sect_id: undefined,
  persona_ids: [],
  pic_id: undefined,
  technique_id: undefined,
  weapon_id: undefined,
  auxiliary_id: undefined,
  alignment: undefined,
  appearance: 7,
  relations: [],
});

const relationOptions = computed(() => [
  {
    label: t("game.info_panel.avatar.relations_list.parent"),
    value: RelationType.TO_ME_IS_PARENT,
  },
  {
    label: t("game.info_panel.avatar.relations_list.child"),
    value: RelationType.TO_ME_IS_CHILD,
  },
  {
    label: t("game.info_panel.avatar.relations_list.sibling"),
    value: RelationType.TO_ME_IS_SIBLING,
  },
  {
    label: t("game.info_panel.avatar.relations_list.master"),
    value: RelationType.TO_ME_IS_MASTER,
  },
  {
    label: t("game.info_panel.avatar.relations_list.apprentice"),
    value: RelationType.TO_ME_IS_DISCIPLE,
  },
  {
    label: t("game.info_panel.avatar.relations_list.lovers"),
    value: RelationType.TO_ME_IS_LOVER,
  },
  {
    label: t("game.info_panel.avatar.relations_list.friend"),
    value: RelationType.TO_ME_IS_FRIEND,
  },
  {
    label: t("game.info_panel.avatar.relations_list.enemy"),
    value: RelationType.TO_ME_IS_ENEMY,
  },
]);

// --- Computed Options ---
const sectOptions = computed(() => {
  if (!gameData.value) return [];
  return gameData.value.sects.map((s) => ({ label: s.name, value: s.id }));
});

const personaOptions = computed(() => {
  if (!gameData.value) return [];
  return gameData.value.personas.map((p) => ({
    label: p.name + ` (${p.desc})`,
    value: p.id,
  }));
});

const realmOptions = computed(() => {
  if (!gameData.value) return [];
  return gameData.value.realms.map((r, idx) => ({
    label: t(`realms.${r}`),
    value: idx * 30 + 1,
  }));
});

const techniqueOptions = computed(() => {
  if (!gameData.value) return [];
  return gameData.value.techniques.map((item) => ({
    label: `${item.name}（${t("attributes." + item.attribute)}·${t("technique_grades." + item.grade)}）`,
    value: item.id,
  }));
});

const weaponOptions = computed(() => {
  if (!gameData.value) return [];
  return gameData.value.weapons.map((w) => ({
    label: `${w.name}（${t("game.info_panel.popup.types." + w.type)}·${t("realms." + w.grade)}）`,
    value: w.id,
  }));
});

const auxiliaryOptions = computed(() => {
  if (!gameData.value) return [];
  return gameData.value.auxiliaries.map((a) => ({
    label: `${a.name}（${t("realms." + a.grade)}）`,
    value: a.id,
  }));
});

const alignmentOptions = computed(() => {
  if (!gameData.value) return [];
  return gameData.value.alignments.map((a) => ({
    label: a.label,
    value: a.value,
  }));
});

const availableAvatars = computed(() => {
  if (!avatarMeta.value) return [];
  const key = createForm.value.gender === "FEMALE" ? "females" : "males";
  return avatarMeta.value[key] || [];
});

const currentAvatarUrl = computed(() => {
  if (!createForm.value.pic_id) return "";
  const dir = createForm.value.gender === "FEMALE" ? "females" : "males";
  return `/assets/${dir}/${createForm.value.pic_id}.png`;
});

const avatarOptions = computed(() => {
  return avatarList.value.map((a) => ({
    label: `[${a.sect_name}] ${a.name}`,
    value: a.id,
  }));
});

// --- Methods ---
async function fetchData() {
  loading.value = true;
  try {
    if (!gameData.value) {
      gameData.value = await avatarApi.fetchGameData();
    }
    if (!avatarMeta.value) {
      avatarMeta.value = await avatarApi.fetchAvatarMeta();
    }
    // 获取角色列表用于关系选择
    const res = await avatarApi.fetchAvatarList();
    avatarList.value = res.avatars;
  } catch (e) {
    message.error(t("game_start.create_avatar.messages.fetch_failed"));
  } finally {
    loading.value = false;
  }
}

function addRelation() {
  if (!createForm.value.relations) {
    createForm.value.relations = [];
  }
  createForm.value.relations.push({
    target_id: "",
    relation: RelationType.TO_ME_IS_FRIEND,
  });
}

function removeRelation(index: number) {
  createForm.value.relations?.splice(index, 1);
}

async function handleCreateAvatar() {
  if (!createForm.value.level && realmOptions.value.length > 0) {
    createForm.value.level = realmOptions.value[0].value as number;
  }

  loading.value = true;
  try {
    const payload = { ...createForm.value };
    // Convert gender for backend if needed (Backend expects '男'/'女' or 'MALE'/'FEMALE'?)
    // Checking CreateAvatarParams in api-docs or common patterns...
    // Usually backend for this starter project used '男'/'女' based on initial code.
    // Let's stick to what it was: '男'/'女' but internal enum is better.
    // I'll check what it was before: gender: '男'
    const backendPayload: any = { ...payload };
    backendPayload.gender = payload.gender === "FEMALE" ? "女" : "男";

    if (!payload.alignment) {
      backendPayload.alignment = "NEUTRAL";
    }

    await avatarApi.createAvatar(backendPayload);
    message.success(t("game_start.create_avatar.messages.create_success"));
    await worldStore.fetchState?.();

    // Reset form
    createForm.value = {
      surname: "",
      given_name: "",
      gender: "MALE",
      age: 16,
      level: realmOptions.value[0]?.value,
      sect_id: undefined,
      persona_ids: [],
      pic_id: undefined,
      technique_id: undefined,
      weapon_id: undefined,
      auxiliary_id: undefined,
      alignment: undefined,
      appearance: 7,
      relations: [],
    };

    emit("created");
  } catch (e) {
    message.error(
      t("game_start.create_avatar.messages.create_failed", {
        error: String(e),
      }),
    );
  } finally {
    loading.value = false;
  }
}

watch(
  () => createForm.value.gender,
  () => {
    createForm.value.pic_id = undefined;
  },
);

watch(
  () => realmOptions.value,
  (options) => {
    if (!createForm.value.level && options.length > 0) {
      createForm.value.level = options[0].value as number;
    }
  },
  { immediate: true },
);

onMounted(() => {
  fetchData();
});
</script>

<template>
  <div class="create-panel">
    <div v-if="loading && !gameData" class="loading">
      {{ t("game_start.create_avatar.loading_data") }}
    </div>
    <div v-else class="create-layout">
      <div class="form-column">
        <n-form label-placement="left" label-width="80">
          <n-form-item :label="t('game_start.create_avatar.labels.name')">
            <div class="name-inputs">
              <n-input
                v-model:value="createForm.surname"
                :placeholder="t('game_start.create_avatar.labels.surname')"
                style="width: 6em"
              />
              <n-input
                v-model:value="createForm.given_name"
                :placeholder="t('game_start.create_avatar.labels.given_name')"
                style="flex: 1"
              />
            </div>
          </n-form-item>
          <n-form-item :label="t('game_start.create_avatar.labels.gender')">
            <n-radio-group v-model:value="createForm.gender">
              <n-radio-button
                value="MALE"
                :label="t('game_start.create_avatar.labels.male')"
              />
              <n-radio-button
                value="FEMALE"
                :label="t('game_start.create_avatar.labels.female')"
              />
            </n-radio-group>
          </n-form-item>
          <n-form-item :label="t('game_start.create_avatar.labels.age')">
            <n-slider
              v-model:value="createForm.age"
              :min="16"
              :max="100"
              :step="1"
            />
            <span style="margin-left: 0.8em; width: 4em"
              >{{ createForm.age
              }}{{ t("game_start.create_avatar.labels.age_unit") }}</span
            >
          </n-form-item>
          <n-form-item :label="t('game_start.create_avatar.labels.realm')">
            <n-select
              v-model:value="createForm.level"
              :options="realmOptions"
              :placeholder="t('game_start.create_avatar.labels.realm')"
            />
          </n-form-item>
          <n-form-item :label="t('game_start.create_avatar.labels.sect')">
            <n-select
              v-model:value="createForm.sect_id"
              :options="sectOptions"
              :placeholder="
                t('game_start.create_avatar.labels.sect_rogue_desc')
              "
              clearable
            />
          </n-form-item>
          <n-form-item :label="t('game_start.create_avatar.labels.persona')">
            <n-select
              v-model:value="createForm.persona_ids"
              multiple
              :options="personaOptions"
              :placeholder="t('game_start.create_avatar.labels.persona')"
              clearable
              max-tag-count="responsive"
            />
          </n-form-item>
          <n-form-item :label="t('game_start.create_avatar.labels.alignment')">
            <n-select
              v-model:value="createForm.alignment"
              :options="alignmentOptions"
              :placeholder="t('ui.create_alignment_placeholder')"
              clearable
            />
          </n-form-item>
          <n-form-item :label="t('game_start.create_avatar.labels.appearance')">
            <div class="appearance-slider">
              <n-slider
                v-model:value="createForm.appearance"
                :min="1"
                :max="10"
                :step="1"
                style="flex: 1; min-width: 0"
              />
              <span>{{ createForm.appearance || 1 }}</span>
            </div>
          </n-form-item>
          <n-form-item :label="t('game_start.create_avatar.labels.technique')">
            <n-select
              v-model:value="createForm.technique_id"
              :options="techniqueOptions"
              :placeholder="t('game_start.create_avatar.labels.technique_desc')"
              clearable
            />
          </n-form-item>
          <n-form-item :label="t('game_start.create_avatar.labels.weapon')">
            <n-select
              v-model:value="createForm.weapon_id"
              :options="weaponOptions"
              :placeholder="t('game_start.create_avatar.labels.weapon_desc')"
              clearable
            />
          </n-form-item>
          <n-form-item :label="t('game_start.create_avatar.labels.auxiliary')">
            <n-select
              v-model:value="createForm.auxiliary_id"
              :options="auxiliaryOptions"
              :placeholder="t('game_start.create_avatar.labels.auxiliary_desc')"
              clearable
            />
          </n-form-item>
          <n-form-item :label="t('game_start.create_avatar.labels.relations')">
            <div class="relations-container">
              <div
                v-for="(rel, index) in createForm.relations"
                :key="index"
                class="relation-row"
              >
                <n-select
                  v-model:value="rel.target_id"
                  :options="avatarOptions"
                  :placeholder="
                    t('game_start.create_avatar.labels.relation_target')
                  "
                  filterable
                  style="width: 12em"
                />
                <n-select
                  v-model:value="rel.relation"
                  :options="relationOptions"
                  :placeholder="
                    t('game_start.create_avatar.labels.relation_type')
                  "
                  style="width: 8em"
                />
                <n-button
                  @click="removeRelation(index)"
                  circle
                  size="small"
                  type="error"
                  >-</n-button
                >
              </div>
              <n-button
                @click="addRelation"
                size="small"
                dashed
                style="width: 100%"
                >+
                {{
                  t("game_start.create_avatar.labels.add_relation")
                }}</n-button
              >
            </div>
          </n-form-item>
          <div class="actions">
            <n-button
              type="primary"
              @click="handleCreateAvatar"
              block
              :loading="loading"
              >{{ t("game_start.create_avatar.actions.create") }}</n-button
            >
          </div>
        </n-form>
      </div>
      <div class="avatar-column">
        <div class="avatar-preview">
          <img
            v-if="currentAvatarUrl"
            :src="currentAvatarUrl"
            alt="Avatar Preview"
          />
          <div v-else class="no-avatar">
            {{ t("game_start.create_avatar.labels.no_avatar") }}
          </div>
        </div>
        <div class="avatar-grid">
          <div
            v-for="id in availableAvatars"
            :key="id"
            class="avatar-option"
            :class="{ selected: createForm.pic_id === id }"
            @click="createForm.pic_id = id"
          >
            <img
              :src="`/assets/${createForm.gender === 'FEMALE' ? 'females' : 'males'}/${id}.png`"
              loading="lazy"
            />
          </div>
          <div v-if="availableAvatars.length === 0" class="no-avatars">
            {{ t("game_start.create_avatar.labels.no_avatars_available") }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.create-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.loading {
  text-align: center;
  color: #888;
  padding: 3em;
}

.create-layout {
  display: flex;
  gap: 1.5em;
  height: 100%;
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
}

.form-column {
  flex: 1;
  min-width: 20em;
}

.avatar-column {
  width: 20em;
  display: flex;
  flex-direction: column;
  gap: 0.8em;
}

.name-inputs {
  display: flex;
  gap: 0.8em;
}

.avatar-preview {
  width: 100%;
  height: 15em;
  border: 1px solid #444;
  border-radius: 0.3em;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #222;
  overflow: hidden;
}

.avatar-preview img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.no-avatar {
  color: #666;
  font-size: 0.85em;
}

.avatar-grid {
  flex: 1;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(4em, 1fr));
  grid-auto-rows: 5em;
  gap: 0.5em;
  padding: 0.4em;
  border: 1px solid #333;
  border-radius: 0.3em;
  min-height: 15em;
}

.avatar-option {
  width: 100%;
  height: 100%;
  border: 2px solid transparent;
  border-radius: 0.4em;
  overflow: hidden;
  cursor: pointer;
  background: #111;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    border-color 0.2s,
    transform 0.2s;
}

.avatar-option:hover {
  border-color: #666;
  transform: translateY(-2px);
}

.avatar-option.selected {
  border-color: #4a9eff;
}

.avatar-option img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 0.15em;
}

.no-avatars {
  grid-column: span 4;
  text-align: center;
  color: #666;
  font-size: 0.85em;
}

.appearance-slider {
  display: flex;
  align-items: center;
  gap: 0.8em;
  flex: 1;
  min-width: 0;
}

.appearance-slider :deep(.n-slider) {
  flex: 1;
  min-width: 0;
}

.appearance-slider span {
  width: 2.5em;
  text-align: right;
  color: #ddd;
}

.relations-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.6em;
}

.relation-row {
  display: flex;
  gap: 0.6em;
  align-items: center;
}

.actions {
  margin-top: 1.5em;
}
</style>
