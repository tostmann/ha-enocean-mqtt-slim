"""
Web UI Application (Starlette) - FIX for Info Modals
"""
import os
import json
import logging
from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from service_state import service_state

logger = logging.getLogger(__name__)
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_PATH = os.path.join(BASE_PATH, 'templates')

async def homepage(request):
    try:
        with open(os.path.join(TEMPLATES_PATH, 'dashboard_new.html'), 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content)
    except Exception as e:
        return HTMLResponse(f"Error loading dashboard: {e}", status_code=500)

async def api_status(request):
    status = service_state.get_status()
    service = service_state.get_service()
    if service:
        status['discovery_active'] = service.is_discovery_active()
        status['discovery_remaining'] = service.get_discovery_time_remaining()
        
        # --- NEW: MQTT Info for Modal ---
        status['mqtt_info'] = {
            'host': service.mqtt_host,
            'port': service.mqtt_port,
            'user': service.mqtt_user if service.mqtt_user else 'None (Anonymous)',
            'connected': False,
            'client_id': 'Unknown',
            'base_topic': 'enocean/'
        }
        if service.mqtt_handler:
            status['mqtt_info']['connected'] = service.mqtt_handler.connected
            status['mqtt_info']['client_id'] = getattr(service.mqtt_handler, 'client_id', 'Unknown')

        # --- NEW: Gateway Info for Modal ---
        status['gateway_info'] = {
            'type': 'Serial' if service.serial_port else 'TCP',
            'address': service.serial_port or service.tcp_address,
            'connected': False,
            'base_id': 'Unknown',
            'version': 'Unknown'
        }
        if service.serial_handler:
            status['gateway_info']['connected'] = getattr(service.serial_handler, 'is_open', False)
            # Versuche Base ID und Version zu lesen (falls im SerialHandler gespeichert)
            if hasattr(service.serial_handler, 'base_id') and service.serial_handler.base_id:
                status['gateway_info']['base_id'] = f"{service.serial_handler.base_id:08x}".upper()
            if hasattr(service.serial_handler, 'version_info') and service.serial_handler.version_info:
                status['gateway_info']['version'] = str(service.serial_handler.version_info)
    else:
        status['discovery_active'] = False
        status['discovery_remaining'] = 0
        status['mqtt_info'] = {}
        status['gateway_info'] = {}

    return JSONResponse(status)

# ... (Rest der Datei: api_discovery_control, api_devices, api_device_detail, api_eep_profiles ist identisch wie vorher) ...
# ... Bitte den restlichen Code aus der vorherigen Version übernehmen oder hier kopieren ...

async def api_discovery_control(request):
    service = service_state.get_service()
    if not service: return JSONResponse({'error': 'Service not ready'}, status_code=503)
    if request.method == 'POST':
        try:
            data = await request.json()
            action = data.get('action')
            if action == 'start':
                service.start_discovery(int(data.get('duration', 60)))
                return JSONResponse({'status': 'started'})
            elif action == 'stop':
                service.stop_discovery()
                return JSONResponse({'status': 'stopped'})
        except Exception as e: return JSONResponse({'error': str(e)}, status_code=400)

async def api_devices(request):
    manager = service_state.get_device_manager()
    if not manager: return JSONResponse({'error': 'Service not ready'}, status_code=503)
    if request.method == 'GET':
        return JSONResponse({'devices': manager.list_devices()})
    elif request.method == 'POST':
        try:
            data = await request.json()
            success = manager.add_device(data.get('id'), data.get('name'), data.get('eep'))
            if success:
                service_state.update_status('devices', len(manager.list_devices()))
                return JSONResponse({'status': 'created'})
            return JSONResponse({'detail': 'Exists'}, status_code=400)
        except Exception as e: return JSONResponse({'detail': str(e)}, status_code=400)

async def api_device_detail(request):
    device_id = request.path_params['device_id']
    manager = service_state.get_device_manager()
    if not manager: return JSONResponse({'error': 'Service not ready'}, status_code=503)
    
    if request.method == 'GET':
        device = manager.get_device(device_id)
        if device: return JSONResponse(device)
        return JSONResponse({'detail': 'Not found'}, status_code=404)
    
    elif request.method == 'PUT':
        data = await request.json()
        service = service_state.get_service()
        if 'provisioning_variant_url' in data and service:
            url = data['provisioning_variant_url']
            vid = data['provisioning_variant_id']
            file_hint = f"PROV-{device_id}-{vid}"
            real_eep = await service._download_and_save_profile(url, file_hint)
            if real_eep:
                data['eep'] = real_eep
                del data['provisioning_variant_url']
                del data['provisioning_variant_id']
            else:
                return JSONResponse({'detail': 'Profile download failed'}, status_code=502)

        old_device = manager.get_device(device_id)
        old_eep = old_device.get('eep') if old_device else None
        
        if manager.update_device(device_id, data):
            if service:
                new_device = manager.get_device(device_id)
                new_eep = new_device.get('eep')
                if old_eep and old_eep != 'pending' and old_eep != new_eep:
                    loader = service_state.get_eep_loader()
                    mqtt = service_state.get_mqtt_handler()
                    if loader and mqtt:
                        prof = loader.get_profile(old_eep)
                        if prof: mqtt.remove_device(device_id, prof.get_entities())
                if new_device.get('enabled') and new_eep != 'pending':
                    await service.publish_device_discovery(new_device)
            return JSONResponse({'status': 'updated'})
        return JSONResponse({'detail': 'Failed'}, status_code=400)
    
    elif request.method == 'DELETE':
        device = manager.get_device(device_id)
        if device:
            mqtt = service_state.get_mqtt_handler()
            loader = service_state.get_eep_loader()
            if mqtt and loader and device.get('eep') != 'pending':
                try:
                    profile = loader.get_profile(device['eep'])
                    if profile:
                        entities = profile.get_entities()
                        mqtt.remove_device(device_id, entities)
                except Exception as e:
                    logger.error(f"Error removing HA entities during delete: {e}")

            if manager.remove_device(device_id):
                service_state.update_status('devices', len(manager.list_devices()))
                if mqtt:
                    mqtt.client.publish(f"enocean/{device_id}/state", "", qos=1, retain=True)
                    mqtt.client.publish(f"enocean/{device_id}/availability", "", qos=1, retain=True)
                return JSONResponse({'status': 'deleted'})
        return JSONResponse({'detail': 'Delete failed or device not found'}, status_code=400)

async def api_eep_profiles(request):
    loader = service_state.get_eep_loader()
    return JSONResponse({'profiles': loader.list_profiles() if loader else []})

routes = [
    Route('/', endpoint=homepage),
    Route('/api/status', endpoint=api_status),
    Route('/api/system/discovery', endpoint=api_discovery_control, methods=['POST']),
    Route('/api/devices', endpoint=api_devices, methods=['GET', 'POST']),
    Route('/api/devices/{device_id}', endpoint=api_device_detail, methods=['GET', 'PUT', 'DELETE']),
    Route('/api/eep-profiles', endpoint=api_eep_profiles),
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
]

app = Starlette(debug=True, routes=routes, middleware=middleware)
