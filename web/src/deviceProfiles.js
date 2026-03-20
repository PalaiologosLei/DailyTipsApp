export const deviceProfiles = [
  { key: 'iphone_17', label: 'iPhone 17', width: 1206, height: 2622 },
  { key: 'iphone_17_air', label: 'iPhone 17 Air', width: 1260, height: 2736 },
  { key: 'iphone_17_pro', label: 'iPhone 17 Pro', width: 1206, height: 2622 },
  { key: 'iphone_17_pro_max', label: 'iPhone 17 Pro Max', width: 1320, height: 2868 },
  { key: 'iphone_17e', label: 'iPhone 17e', width: 1170, height: 2532 },
  { key: 'iphone_16', label: 'iPhone 16', width: 1179, height: 2556 },
  { key: 'iphone_16_plus', label: 'iPhone 16 Plus', width: 1290, height: 2796 },
  { key: 'iphone_16_pro', label: 'iPhone 16 Pro', width: 1206, height: 2622 },
  { key: 'iphone_16_pro_max', label: 'iPhone 16 Pro Max', width: 1320, height: 2868 },
  { key: 'custom', label: 'Custom', width: 1206, height: 2622 },
]

export function getDeviceProfile(key) {
  return deviceProfiles.find((profile) => profile.key === key) ?? deviceProfiles[2]
}
