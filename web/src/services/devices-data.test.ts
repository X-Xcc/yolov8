import { describe, expect, it } from 'vitest';
import { CameraStatus } from '../types';
import {
  buildBatchCameraPayload,
  createSelectedDiscoverySet,
  DEFAULT_DEVICE_FORM,
  getOnlineCameraCount,
  toDeviceForm,
  toDevicePayload,
  toggleSelectedDiscovery,
} from './devices-data';

describe('devices data helpers', () => {
  it('normalizes usb form payload to numeric address', () => {
    expect(toDevicePayload({ ...DEFAULT_DEVICE_FORM, name: 'USB Cam', type: 'usb', address: '2' })).toMatchObject({
      name: 'USB Cam',
      type: 'usb',
      address: 2,
    });
  });

  it('builds edit form state from existing camera', () => {
    expect(toDeviceForm({
      id: 'cam-1',
      name: 'Front Gate',
      type: 'rtsp',
      address: 'rtsp://demo',
      status: CameraStatus.ONLINE,
      user: 'admin',
      password: '1234',
      streamUrl: '/video_feed?cam=cam-1',
      personCount: 0,
    } as any)).toEqual({
      name: 'Front Gate',
      type: 'rtsp',
      address: 'rtsp://demo',
      user: 'admin',
      password: '1234',
    });
  });

  it('creates and toggles discovery selections by ip', () => {
    const discovered = [
      { ip: '192.168.1.10', name: 'Cam A' },
      { ip: '192.168.1.11', name: 'Cam B' },
    ] as any;

    const selected = createSelectedDiscoverySet(discovered);
    expect([...selected]).toEqual(['192.168.1.10', '192.168.1.11']);

    expect([...toggleSelectedDiscovery(selected, '192.168.1.11', false)]).toEqual(['192.168.1.10']);
  });

  it('builds batch camera payload from selected discoveries', () => {
    const discovered = [
      { ip: '192.168.1.10', name: 'Cam A', rtspUrl: 'rtsp://a', brand: 'Hik', model: 'DS' },
      { ip: '192.168.1.11', name: 'Cam B', rtspUrl: 'rtsp://b' },
    ] as any;

    expect(buildBatchCameraPayload(discovered, new Set(['192.168.1.11']))).toEqual([
      {
        name: 'Cam B',
        type: 'rtsp',
        address: 'rtsp://b',
        ip: '192.168.1.11',
        brand: undefined,
        model: undefined,
        port: 554,
      },
    ]);
  });

  it('counts online devices from camera list', () => {
    expect(getOnlineCameraCount([
      { id: '1', status: CameraStatus.ONLINE },
      { id: '2', status: CameraStatus.OFFLINE },
      { id: '3', status: CameraStatus.ONLINE },
    ] as any)).toBe(2);
  });
});
