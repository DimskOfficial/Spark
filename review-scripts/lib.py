import os, re
R='/data/Spark/'
def edit(path, fn):
    p=R+path
    if not os.path.exists(p): print('MISSING',path); return
    s=open(p).read(); n=fn(s)
    if n!=s: open(p,'w').write(n); print('fixed',path)
    else: print('nochange',path)
def rep(s, old, new, must=True, count=1):
    if old not in s:
        if must: raise SystemExit('PATTERN NOT FOUND:\n'+old[:300])
        return s
    return s.replace(old,new,count)
def wgpu30(s):
    s=s.replace('device.on_uncaptured_error(Box::new(|e| {','device.on_uncaptured_error(Arc::new(|e| {')
    s=s.replace('wgpu::Error::Validation { source, .. } => log::error!("GPU validation error: {source}")','wgpu::Error::Validation { description, .. } => log::error!("GPU validation error: {description}")')
    s=s.replace('wgpu::Error::Internal { source, .. } => log::error!("GPU internal error: {source}")','wgpu::Error::Internal { description, .. } => log::error!("GPU internal error: {description}")')
    s=s.replace('include_str!("../spark-core/src/shaders/','include_str!("../../spark-core/src/shaders/')
    s=s.replace('entry_point: "skybox_vs"','entry_point: Some("skybox_vs")').replace('entry_point: "skybox_fs"','entry_point: Some("skybox_fs")')
    s=s.replace('''                depth_write_enabled: false,
                depth_compare: wgpu::CompareFunction::LessEqual,''','''                depth_write_enabled: Some(false),
                depth_compare: Some(wgpu::CompareFunction::LessEqual),''')
    s=s.replace('''            multiview: None,
            cache: None,''','''            multiview_mask: None,
            cache: None,''')
    s=s.replace('let row_bytes = *w as u64 * 4;\n                let padded = row_bytes.div_ceil(wgpu::COPY_BYTES_PER_ROW_ALIGNMENT) * wgpu::COPY_BYTES_PER_ROW_ALIGNMENT;','let row_bytes = *w * 4;\n                let padded = u64::from(row_bytes.div_ceil(wgpu::COPY_BYTES_PER_ROW_ALIGNMENT) * wgpu::COPY_BYTES_PER_ROW_ALIGNMENT);')
    s=s.replace('''    let available: Vec<String> = instance
        .enumerate_adapters()
        .iter()''','''    let available: Vec<String> = pollster::block_on(instance.enumerate_adapters(wgpu::Backends::all()))
        .iter()''')
    return s
