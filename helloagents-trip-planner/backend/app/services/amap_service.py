"""高德地图HTTP服务 - 直接调用高德地图Web API"""
import re
import json
from typing import List, Dict, Any, Optional
from langchain_core.tools import StructuredTool
from ..config import get_settings
from ..models.schemas import Location, POIInfo, WeatherInfo, RouteInfo
import httpx


# 全局HTTP客户端实例
_http_client = None


def get_http_client() -> httpx.AsyncClient:
    """获取全局HTTP客户端实例"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client


async def search_poi(keywords: str, city: str, citylimit: bool = True) -> List[POIInfo]:
    """
    搜索POI - 直接调用高德地图Web API

    Args:
        keywords: 搜索关键词
        city: 城市
        citylimit: 是否限制在城市范围内

    Returns:
        POI信息列表
    """
    settings = get_settings()
    client = get_http_client()

    try:
        params = {
            "keywords": keywords,
            "city": city,
            "citylimit": citylimit,
            "output": "json",
            "key": settings.amap_app_code
        }

        # 后端HTTP API调用只使用AMAP_APP_CODE (Web服务API)
        response = await client.get(
            "https://restapi.amap.com/v3/place/text",
            params=params,
        )

        data = response.json()

        print(f"[INFO] POI搜索API响应: {data.get('status')}")

        # 检查API调用是否成功
        if data.get("status") != "1":
            error_msg = data.get("info", "未知错误")
            print(f"❌ POI搜索API错误: {error_msg}")
            return []

        pois = []
        if "pois" in data and isinstance(data["pois"], list):
            for poi_data in data["pois"][:10]:  # 限制返回前10条
                location_str = poi_data.get("location", "")
                longitude, latitude = 0.0, 0.0
                if location_str:
                    try:
                        lon, lat = location_str.split(",")
                        longitude = float(lon)
                        latitude = float(lat)
                    except:
                        pass

                poi = POIInfo(
                    id=poi_data.get("id", ""),
                    name=poi_data.get("name", ""),
                    address=poi_data.get("address", ""),
                    location=Location(longitude=longitude, latitude=latitude),
                    tel=poi_data.get("tel", ""),
                    type=poi_data.get("type", ""),
                )
                pois.append(poi)

        return pois

    except Exception as e:
        print(f"❌ POI搜索失败（API调用）: {str(e)}")
        print(f"   将返回模拟数据")
        return _get_mock_pois(keywords, city)


async def get_weather(city: str) -> List[WeatherInfo]:
    """
    查询天气 - 直接调用高德地图Web API

    Args:
        city: 城市名称

    Returns:
        天气信息列表
    """
    settings = get_settings()
    client = get_http_client()

    try:
        params = {"city": city, "extensions": "all"}

        # 后端HTTP API调用只使用AMAP_APP_CODE (Web服务API)
        # AMAP_API_KEY是WebJS服务密钥，用于前端地图展示，不应在后端使用
        response = await client.get(
            "https://restapi.amap.com/v3/weather/weatherInfo",
            params=params,
            headers={"Authorization": f"APPCODE {settings.amap_app_code}"}
        )

        data = response.json()

        print(f"[INFO] 天气查询API响应: {data.get('status')}")

        # 检查API调用是否成功
        if data.get("status") != "1":
            error_msg = data.get("info", "未知错误")
            print(f"❌ 天气查询API错误: {error_msg}")
            return []

        weathers = []
        if "forecasts" in data and isinstance(data["forecasts"], list):
            for forecast in data["forecasts"]:
                if isinstance(forecast, dict):
                    weather = WeatherInfo(
                        date=forecast.get("date", ""),
                        day_weather=forecast.get("dayweather", ""),
                        night_weather=forecast.get("nightweather", ""),
                        day_temp=forecast.get("daytemp", ""),
                        night_temp=forecast.get("nighttemp", ""),
                        wind_direction=forecast.get("daywind", ""),
                        wind_power=forecast.get("daypower", ""),
                    )
                    weathers.append(weather)

        return weathers

    except Exception as e:
        print(f"❌ 天气查询失败（API调用）: {str(e)}")
        print(f"   将返回模拟数据")
        return _get_mock_weather(city)


async def plan_route(
    origin_address: str,
    destination_address: str,
    origin_city: Optional[str] = None,
    destination_city: Optional[str] = None,
    route_type: str = "walking"
) -> Optional[RouteInfo]:
    """
    规划路线 - 直接调用高德地图Web API

    Args:
        origin_address: 起点地址
        destination_address: 终点地址
        origin_city: 起点城市
        destination_city: 终点城市
        route_type: 路线类型 (walking/driving/transit)

    Returns:
        路线信息
    """
    settings = get_settings()
    client = get_http_client()

    try:
        # 根据路线类型选择API
        if route_type == "driving":
            api_url = "https://restapi.amap.com/v3/direction/driving"
        elif route_type == "transit":
            api_url = "https://restapi.amap.com/v3/direction/transit/integrated"
        else:  # walking
            api_url = "https://restapi.amap.com/v3/direction/walking"

        params = {
            "origin": origin_address,
            "destination": destination_address
        }

        if route_type == "transit":
            if origin_city:
                params["origin_city"] = origin_city
            if destination_city:
                params["destination_city"] = destination_city
        else:
            if origin_city:
                params["origin_city"] = origin_city
            if destination_city:
                params["destination_city"] = destination_city

        # 后端HTTP API调用只使用AMAP_APP_CODE (Web服务API)
        # AMAP_API_KEY是WebJS服务密钥，用于前端地图展示，不应在后端使用
        response = await client.get(
            api_url,
            params=params,
            headers={"Authorization": f"APPCODE {settings.amap_app_code}"}
        )

        data = response.json()

        print(f"[INFO] 路线规划API响应: {data.get('status')}")

        # 检查API调用是否成功
        if data.get("status") != "1":
            error_msg = data.get("info", "未知错误")
            print(f"❌ 路线规划API错误: {error_msg}")
            return None

        # 提取路线数据
        if "route" in data and "paths" in data["route"]:
            first_path = data["route"]["paths"][0]
            route = RouteInfo(
                distance=float(first_path.get("distance", 0)),
                duration=int(first_path.get("duration", 0)),
                route_type=route_type,
                description=json.dumps(first_path.get("steps", []), ensure_ascii=False, indent=2)
            )
            return route

        return None

    except Exception as e:
        print(f"❌ 路线规划失败（API调用）: {str(e)}")
        print(f"   将返回模拟数据")
        return _get_mock_route(origin_address, destination_address)


def collect_json(result: str) -> Dict[str, Any]:
    """从结果中提取JSON"""
    json_match = re.search(r'\{.*\}', result, re.DOTALL)
    if not json_match:
        print("⚠️  无法从结果中提取JSON")
        return {}

    json_str = json_match.group()
    data = json.loads(json_str)
    return data


# ============ 模拟数据生成（降级方案） ============

def _get_mock_pois(keywords: str, city: str) -> List[POIInfo]:
    """生成模拟POI数据"""
    print(f"   返回模拟POI数据: {keywords} in {city}")

    # 根据关键词生成不同的模拟数据
    poi_name = {
        "景点": f"{city}著名景点",
        "美食": f"{city}特色美食",
        "酒店": f"{city}优质酒店"
    }.get(keywords, f"{keywords} in {city}")

    pois = []
    for i in range(3):
        pois.append(POIInfo(
            id=f"mock_{i}",
            name=f"{poi_name}_{i+1}",
            address=f"{city}市{['朝阳区', '海淀区', '东城区'][i % 3]}",
            location=Location(
                longitude=116.397128 + i * 0.001,
                latitude=39.916527 + i * 0.001
            ),
            tel="010-12345678",
            type="景点" if "景点" in keywords else "酒店"
        ))

    return pois


def _get_mock_weather(city: str) -> List[WeatherInfo]:
    """生成模拟天气数据"""
    print(f"   返回模拟天气数据: {city}")

    # 生成未来3天的模拟天气
    weathers = []
    from datetime import datetime, timedelta

    today = datetime.now()
    for i in range(3):
        date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        weathers.append(WeatherInfo(
            date=date,
            day_weather="晴",
            night_weather="多云",
            day_temp=25 + i,
            night_temp=15 + i,
            wind_direction="南风",
            wind_power="1-3级"
        ))

    return weathers


def _get_mock_route(origin: str, destination: str) -> Optional[RouteInfo]:
    """生成模拟路线数据"""
    print(f"   返回模拟路线数据: {origin} -> {destination}")

    return RouteInfo(
        distance=5000.0,
        duration=600,
        route_type="walking",
        description="模拟路线数据"
    )


# ============ LangChain工具 ============

def create_amap_tools():
    """创建AMAP相关的LangChain工具"""
    from ..services.amap_service import get_amap_service

    async def search_poi_tool(keywords: str, city: str) -> str:
        """搜索POI（景点、酒店等）"""
        try:
            pois = await search_poi(keywords, city)
            return json.dumps([{"name": p.name, "address": p.address} for p in pois], ensure_ascii=False, indent=2)
        except Exception as e:
            return f"搜索失败: {str(e)}"

    async def get_weather_tool(city: str) -> str:
        """查询城市天气"""
        try:
            weathers = await get_weather(city)
            return json.dumps([{"date": w.date, "day_weather": w.day_weather} for w in weathers], ensure_ascii=False, indent=2)
        except Exception as e:
            return f"查询失败: {str(e)}"

    async def plan_route_tool(**kwargs) -> str:
        """规划两点之间的路线"""
        try:
            route = await plan_route(**kwargs)
            if route:
                return json.dumps({
                    "distance": route.distance,
                    "duration": route.duration,
                    "route_type": route.route_type
                }, ensure_ascii=False, indent=2)
            return "路线规划失败"
        except Exception as e:
            return f"路线规划失败: {str(e)}"

    langchain_tools = [
        StructuredTool.from_function(
            name="search_poi",
            description="搜索POI（景点、酒店等），参数：keywords（关键词）、city（城市）",
            coroutine=search_poi_tool
        ),
        StructuredTool.from_function(
            name="get_weather",
            description="查询指定城市的天气信息，参数：city（城市名称）",
            coroutine=get_weather_tool
        ),
        StructuredTool.from_function(
            name="plan_route",
            description="规划两点之间的路线，参数：origin_address（起点地址）、destination_address（终点地址）、origin_city（起点城市，可选）、destination_city（终点城市，可选）、route_type（路线类型：walking/driving/transit，默认walking）",
            coroutine=plan_route_tool
        )
    ]

    return langchain_tools


class AmapService:
    """高德地图服务封装类"""

    def __init__(self):
        """初始化服务"""
        pass

    async def search_poi(self, keywords: str, city: str, citylimit: bool = True) -> List[POIInfo]:
        """搜索POI - 使用HTTP API"""
        return await search_poi(keywords, city, citylimit)

    async def get_weather(self, city: str) -> List[WeatherInfo]:
        """查询天气 - 使用HTTP API"""
        return await get_weather(city)

    async def plan_route(
        self,
        origin_address: str,
        destination_address: str,
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
        route_type: str = "walking"
    ) -> Optional[RouteInfo]:
        """规划路线 - 使用HTTP API"""
        return await plan_route(origin_address, destination_address, origin_city, destination_city, route_type)

    async def get_poi_detail(self, poi_id: str) -> Optional[dict]:
        """
        获取POI详情 - 使用HTTP API

        Args:
            poi_id: POI ID

        Returns:
            POI详情数据
        """
        settings = get_settings()
        client = get_http_client()

        try:
            params = {
                "key": poi_id,
                "extensions": "base"
            }

            # 后端HTTP API调用只使用AMAP_APP_CODE (Web服务API)
            # AMAP_API_KEY是WebJS服务密钥，用于前端地图展示，不应在后端使用
            response = await client.get(
                "https://restapi.amap.com/v3/place/detail",
                params=params,
                headers={"Authorization": f"APPCODE {settings.amap_app_code}"}
            )

            data = response.json()

            if data.get("status") == "1" and data.get("pois"):
                return data["pois"][0]

            return None

        except Exception as e:
            print(f"[ERROR] 获取POI详情失败: {str(e)}")
            print(f"   返回模拟数据")
            return self._get_mock_poi_detail(poi_id)

    def _get_mock_poi_detail(self, poi_id: str) -> dict:
        """生成模拟POI详情数据"""
        return {
            "id": poi_id,
            "name": f"模拟景点详情 - {poi_id}",
            "type": "景点",
            "typecode": "B0000",
            "tel": "010-12345678",
            "address": "模拟地址",
            "location": "116.397128,39.916527",
            "pname": "北京市",
            "cityname": "北京市",
            "adname": "东城区",
            "distance": "0米",
            "biz_ext": {},
            "ecinfo": {"shopid": "", "category": "景点"},
            "photos": {
                "count": 0,
                "photos": []
            },
            "entry": "",
            "cost": [],
            "detail": 1,
            "tips": {},
            "bestvisittime": "",
            "station": "",
            "children": []
        }

    async def geocode(self, address: str, city: Optional[str] = None) -> Optional[Location]:
        """
        地理编码(地址转坐标) - 使用HTTP API

        Args:
            address: 地址
            city: 城市

        Returns:
            经纬度坐标
        """
        settings = get_settings()
        client = get_http_client()

        try:
            params = {"address": address}
            if city:
                params["city"] = city

            # 后端HTTP API调用只使用AMAP_APP_CODE (Web服务API)
            # AMAP_API_KEY是WebJS服务密钥，用于前端地图展示，不应在后端使用
            response = await client.get(
                "https://restapi.amap.com/v3/geocode/geo",
                params=params,
                headers={"Authorization": f"APPCODE {settings.amap_app_code}"}
            )

            data = response.json()

            if data.get("status") == "1" and data.get("geocodes"):
                location_str = data["geocodes"][0].get("location", "")
                if location_str:
                    lon, lat = location_str.split(",")
                    return Location(longitude=float(lon), latitude=float(lat))

            return None

        except Exception as e:
            print(f"[ERROR] 地理编码失败: {str(e)}")
            return None


# 单例模式
_amap_service = None


def get_amap_service() -> AmapService:
    """获取高德地图服务实例(单例模式)"""
    global _amap_service
    if _amap_service is None:
        _amap_service = AmapService()
    return _amap_service


def get_mcp_tools():
    """获取AMAP工具列表（兼容旧接口）"""
    return create_amap_tools()
