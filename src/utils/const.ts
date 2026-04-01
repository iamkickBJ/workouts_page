// const
// 建议通过 VITE_MAPBOX_TOKEN 注入，避免把 token 提交到仓库里
const MAPBOX_TOKEN = (import.meta.env.VITE_MAPBOX_TOKEN || '').trim();
const MAPBOX_TOKEN_IS_VALID = MAPBOX_TOKEN.startsWith('pk.');

const MUNICIPALITY_CITIES_ARR = [
  '北京市',
  '上海市',
  '天津市',
  '重庆市',
  '香港特别行政区',
  '澳门特别行政区',
];

const MAP_LAYER_LIST = [
  'road-label',
  'waterway-label',
  'natural-line-label',
  'natural-point-label',
  'water-line-label',
  'water-point-label',
  'poi-label',
  'airport-label',
  'settlement-subdivision-label',
  'settlement-label',
  'state-label',
  'country-label',
];

// styling: set to `true` if you want dash-line route
const USE_DASH_LINE = true;
// styling: route line opacity: [0, 1]
const LINE_OPACITY = 0.4;
// styling: map height
const MAP_HEIGHT = 600;
//set to `false` if you want to hide the road label characters
const ROAD_LABEL_DISPLAY = true;

// IF you outside China please make sure IS_CHINESE = false
const IS_CHINESE = true;
const USE_ANIMATION_FOR_GRID = false;
const CHINESE_INFO_MESSAGE = (yearLength: number, year: string): string =>
  `户外运动 ${yearLength} 年 ` + (year === 'Total' ? '' : `，地图展示的是 ${year} 年的轨迹`);

const ENGLISH_INFO_MESSAGE = (yearLength: number, year: string): string =>
  `Logged ${yearLength} Years of Outdoor Journey` + (year === 'Total' ? '' : `, the map show routes in ${year}`);

// not support English for now
const CHINESE_LOCATION_INFO_MESSAGE_FIRST =
  '我去过了一些地方，希望随着时间推移，地图点亮的地方越来越多';
const CHINESE_LOCATION_INFO_MESSAGE_SECOND = '不要停下来，不要停下探索的脚步';

const INFO_MESSAGE = IS_CHINESE ? CHINESE_INFO_MESSAGE : ENGLISH_INFO_MESSAGE;
const TOTAL_LABEL = IS_CHINESE ? '总计' : 'Total';
const JOURNEY_LABEL = IS_CHINESE ? ' 运动旅程' : ' Journey';
const STREAK_LABEL = IS_CHINESE ? ' 连续天数' : ' Streak';
const AVG_HEART_RATE_LABEL = IS_CHINESE ? ' 平均心率' : ' Avg Heart Rate';
const HEATMAP_LABEL = IS_CHINESE ? '热力图' : 'Heatmap';
const YEAR_LABEL = IS_CHINESE ? '年份' : 'Year';
const CITY_LABEL = IS_CHINESE ? '城市' : 'City';
const TITLE_LABEL = IS_CHINESE ? '标题' : 'Title';
const TYPE_LABEL = IS_CHINESE ? '类型' : 'Type';
const PACE_LABEL = IS_CHINESE ? '配速' : 'Pace';
const TIME_LABEL = IS_CHINESE ? '时长' : 'Time';
const DATE_LABEL = IS_CHINESE ? '日期' : 'Date';
const HEART_RATE_SHORT_LABEL = IS_CHINESE ? '心率' : 'BPM';
const DISTANCE_UNIT_LABEL = ' KM';
const FAILED_TO_LOAD_SVG_LABEL = IS_CHINESE ? 'SVG 加载失败' : 'Failed to load SVG';
const LOADING_LABEL = IS_CHINESE ? '加载中...' : 'loading...';
const NO_MAP_DATA_LABEL = IS_CHINESE ? '(这条运动没有地图轨迹)' : '(No map data for this workout)';
const MAP_TOKEN_MISSING_LABEL = IS_CHINESE
  ? '地图未显示：请在 GitHub 仓库 Secrets 中配置 MAPBOX_TOKEN（或 VITE_MAPBOX_TOKEN）'
  : 'Map hidden: set MAPBOX_TOKEN (or VITE_MAPBOX_TOKEN) in GitHub Secrets.';
const MAP_TOKEN_INVALID_LABEL = IS_CHINESE
  ? '地图未显示：Mapbox Token 无效，请使用 pk. 开头的 Public Token'
  : 'Map hidden: invalid Mapbox token, please use a public token starting with pk.';

// 定义各种运动的标题
const FULL_MARATHON_RUN_TITLE = IS_CHINESE ? '全程马拉松' : 'Full Marathon';
const HALF_MARATHON_RUN_TITLE = IS_CHINESE ? '半程马拉松' : 'Half Marathon';
const RUN_TITLE = IS_CHINESE ? '跑步' : 'Run';
const TRAIL_RUN_TITLE = IS_CHINESE ? '越野跑' : 'Trail Run';
const SWIM_TITLE = IS_CHINESE ? '游泳' : 'Swim';

const RIDE_TITLE = IS_CHINESE ? '骑行' : 'Ride';
const INDOOR_RIDE_TITLE = IS_CHINESE ? '室内骑行' : 'Indoor Ride';
const VIRTUAL_RIDE_TITLE = IS_CHINESE ? '虚拟骑行' : 'Virtual Ride';
const HIKE_TITLE = IS_CHINESE ? '徒步' : 'Hike';
const ROWING_TITLE = IS_CHINESE ? '划船' : 'Rowing';
const KAYAKING_TITLE = IS_CHINESE ? '皮划艇' : 'Kayaking';
const SNOWBOARD_TITLE = IS_CHINESE ? '单板滑雪' : 'Snowboard';
const SKI_TITLE = IS_CHINESE ? '双板滑雪' : 'Ski';
const ROAD_TRIP_TITLE = IS_CHINESE ? '自驾' : 'RoadTrip';
const FLIGHT_TITLE = IS_CHINESE ? '飞行' : 'Flight';

const RUN_TITLES = {
  FULL_MARATHON_RUN_TITLE,
  HALF_MARATHON_RUN_TITLE,
  RUN_TITLE,
  TRAIL_RUN_TITLE,
  RIDE_TITLE,
  INDOOR_RIDE_TITLE,
  VIRTUAL_RIDE_TITLE,
  HIKE_TITLE,
  ROWING_TITLE,
  KAYAKING_TITLE,
  SWIM_TITLE,
  ROAD_TRIP_TITLE,
  FLIGHT_TITLE,
  SNOWBOARD_TITLE,
  SKI_TITLE,
};

// ⚠️ 核心修改：这里添加了映射关系，网页才会显示对应的 Tab
const TYPE_TRANSLATE = {
  Run: RUN_TITLE,
  Ride: RIDE_TITLE,
  VirtualRide: VIRTUAL_RIDE_TITLE, // 👈 这一行让虚拟骑行单独显示
  Hike: HIKE_TITLE,
  Swim: SWIM_TITLE,
  Rowing: ROWING_TITLE,
  Kayaking: KAYAKING_TITLE,
  Snowboard: SNOWBOARD_TITLE,
  Ski: SKI_TITLE,
  RoadTrip: ROAD_TRIP_TITLE,
  Flight: FLIGHT_TITLE,
};

const nike = 'rgb(77, 210, 255)';
const yellow = 'rgb(77, 210, 255)';
const green = 'rgb(77, 210, 255)'; // Unified Premium Azure
const pink = 'rgb(237,85,219)';
const cyan = 'rgb(112,243,255)';
const IKB = 'rgb(0,47,167)';
const wpink = 'rgb(228,212,220)';
const gold = 'rgb(242,190,69)';
const purple = 'rgb(154,118,252)';
const veryPeri = 'rgb(105,106,173)'; // 长春花蓝 (用于虚拟骑行)
const red = 'rgb(255,0,0)'; // 大红色

// If your map has an offset please change this line
// issues #92 and #198
export const NEED_FIX_MAP = false;
export const MAIN_COLOR = green;
export const RUN_COLOR = green;
export const RIDE_COLOR = green;
export const VIRTUAL_RIDE_COLOR = green; // 虚拟骑行同步统一
export const HIKE_COLOR = green;
export const SWIM_COLOR = green;
export const ROWING_COLOR = green;
export const ROAD_TRIP_COLOR = green;
export const FLIGHT_COLOR = green;
export const PROVINCE_FILL_COLOR = '#47b8e0';
export const COUNTRY_FILL_COLOR = wpink;
export const KAYAKING_COLOR = red;
export const SNOWBOARD_COLOR = wpink;
export const TRAIL_RUN_COLOR = IKB;

// 导出所有配置
export {
  AVG_HEART_RATE_LABEL,
  CHINESE_LOCATION_INFO_MESSAGE_FIRST,
  CHINESE_LOCATION_INFO_MESSAGE_SECOND,
  CITY_LABEL,
  DATE_LABEL,
  DISTANCE_UNIT_LABEL,
  FAILED_TO_LOAD_SVG_LABEL,
  HEART_RATE_SHORT_LABEL,
  HEATMAP_LABEL,
  MAPBOX_TOKEN,
  MAPBOX_TOKEN_IS_VALID,
  MUNICIPALITY_CITIES_ARR,
  MAP_LAYER_LIST,
  IS_CHINESE,
  JOURNEY_LABEL,
  LOADING_LABEL,
  NO_MAP_DATA_LABEL,
  MAP_TOKEN_MISSING_LABEL,
  MAP_TOKEN_INVALID_LABEL,
  PACE_LABEL,
  ROAD_LABEL_DISPLAY,
  STREAK_LABEL,
  TIME_LABEL,
  TITLE_LABEL,
  TOTAL_LABEL,
  TYPE_LABEL,
  YEAR_LABEL,
  INFO_MESSAGE,
  RUN_TITLES,
  USE_ANIMATION_FOR_GRID,
  USE_DASH_LINE,
  LINE_OPACITY,
  MAP_HEIGHT,
  TYPE_TRANSLATE, // 👈 确保这里导出了
};
