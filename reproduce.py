"""单个冻结168小时窗口的审稿复现；输入为处理/构造数据。"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, math, platform
import subprocess, sys, time, traceback

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd

CASES = [('reference', 0., False), ('production_only', 0., True),
         ('storage_only', 20., False), ('joint', 20., True)]
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path, value):
    # 证据文件独占创建，不覆盖旧结果或发生rename持久化问题。
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)

def nz(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}

def inputs():
    config = read(ROOT / 'config.json')
    for name, expected in read(ROOT / 'frozen-inputs.json').items():
        assert sha(ROOT / name) == expected, ('冻结输入/内核变化', name)
    x = nz(ROOT / config['input'])
    price = nz(ROOT / config['price'])['price_CNY_per_MWh']
    assert x['qref'].shape == (168, 4) and price.shape == (168,)
    assert all(np.isfinite(v).all() for v in x.values())
    return config, x, price

def audit(sol, x, price, params, cap, flex, peak, fee):
    """直接用保存物理量重建，不导入内核或MILP矩阵。"""
    q, stock = sol['q'], sol['inventory']
    grid, ch, dis, soc, mode = [sol[k] for k in ('grid_MWh','charge_MWh','discharge_MWh','soc_MWh','charge_mode')]
    obs, q0, k = x['observed'], x['qref'], x['k']
    load = obs + (q - q0) * k
    eta = math.sqrt(params['roundtrip_efficiency'])
    power = cap * params['power_ratio_per_h']
    errors = {}
    def ck(name, value, upper=False):
        array = np.asarray(value)
        assert np.isfinite(array).all(), name
        errors[name] = float(max(0., array.max()) if upper else np.abs(array).max())
    assert all(np.isfinite(v).all() for v in sol.values())
    assert q.shape == (168,4) and stock.shape == (169,3) and soc.shape == (169,)
    ck('coefficient', sol['k'] - k)
    ck('flow_vehicle', np.diff(stock, axis=0) - q[:,:3] + q[:,1:])
    ck('inventory_initial_vehicle', stock[0] - x['inventory_start'][0])
    ck('inventory_final_vehicle', stock[-1] - x['inventory_end'][-1])
    ck('inventory_bounds_vehicle', np.maximum(-stock, stock - [606,20,116]), True)
    active = np.repeat(q0[:,3].reshape(7,24).sum(axis=1)>1e-8,24) & (np.arange(168)%24<20)
    ck('capacity_vehicle', q[:,:3] - active[:,None]*[120,70,70], True)
    ck('negative_production_vehicle', -q, True)
    ck('fixed_production_vehicle', q[:,[0,3]] - q0[:,[0,3]])
    if not flex: ck('all_fixed_production_vehicle', q-q0)
    ck('production_total_vehicle', q.sum(axis=0)-q0.sum(axis=0))
    ck('shop_load_map_MWh', sol['shop_load_MWh']-load)
    ck('shop_energy_total_MWh', load.sum(axis=0)-obs.sum(axis=0))
    ck('negative_shop_MWh', -load, True)
    ck('production_radius_vehicle', np.abs(q[:,1:3]-q0[:,1:3])-70*params['production_radius'], True)
    ck('energy_radius_MWh', np.abs(load-obs)-obs*params['energy_radius'], True)
    ck('power_balance_MWh', grid+x['pv']+dis-load.sum(axis=1)-x['aux']-ch)
    ck('grid_bounds_MW', np.maximum(-grid, grid-peak), True)
    ck('soc_recurrence_MWh', np.diff(soc)-eta*ch+dis/eta)
    ck('soc_endpoints_MWh', soc[[0,-1]]-cap*params['soc_initial'])
    ck('soc_bounds_MWh', np.maximum(cap*params['soc_min']-soc,soc-cap*params['soc_max']),True)
    ck('power_bounds_MWh', np.maximum(np.maximum(-ch,-dis),np.maximum(ch-power,dis-power)),True)
    ck('mode_bounds', np.maximum(-mode,mode-(1 if cap else 0)),True)
    ck('mode_integrality', mode-np.round(mode))
    ck('mode_charge_MWh', ch-power*mode,True)
    ck('mode_discharge_MWh', dis-power*(1-mode),True)
    ck('simultaneous_MWh', np.minimum(ch,dis),True)
    ck('daily_discharge_MWh',dis.reshape(7,24).sum(axis=1)-cap*params['daily_discharge_ratio'],True)
    g0 = obs.sum(axis=1)+x['aux']-x['pv']
    loss = (1-eta)*math.fsum(ch)+(1/eta-1)*math.fsum(dis)
    ck('loss_purchase_identity_MWh', math.fsum(grid)-math.fsum(g0)-loss)
    cost = math.fsum(float(g)*float(p+fee) for g,p in zip(grid,price))
    cost0 = math.fsum(float(g)*float(p+fee) for g,p in zip(g0,price))
    ck('no_worse_than_reference_CNY',cost-cost0-.001,True)
    assert max(errors.values()) <= 1e-5, errors
    return {'status': 'PASS_ALGEBRAIC_ONLY', 'errors': errors, 'energy_charge_CNY': cost,
            'reference_CNY':cost0, 'storage_loss_MWh':loss,'max_hourly_grid_MW':float(grid.max())}

def child(label):
    config,x,price = inputs()
    cap,flex = next((cap,flex) for name,cap,flex in CASES if name==label)
    spec = importlib.util.spec_from_file_location('frozen_kernel',ROOT/config['kernel'])
    kernel = importlib.util.module_from_spec(spec); spec.loader.exec_module(kernel)
    f = pd.DataFrame(x['observed'],columns=kernel.COLS)
    f['timestamp']=pd.to_datetime(x['timestamp_ns']);f['energy_usable']=True
    f['Ele_NonProduction_MWh']=x['aux'];f['Ele_PV_Generation_MWh']=x['pv']
    f['Ele_Plant_Total_MWh']=x['observed'].sum(axis=1)+x['aux']
    f['price']=(price+config['fee_CNY_per_MWh'])/1000
    for j,s in enumerate(kernel.SHOPS):f[s+'_vehicle']=x['qref'][:,j]
    for j,b in enumerate(kernel.BUFFERS):
        f[b+'_start_vehicle']=x['inventory_start'][:,j];f[b+'_end_vehicle']=x['inventory_end'][:,j]
    peak=float((x['observed'].sum(axis=1)+x['aux']-x['pv']).max())
    # 独占调用凭证先落盘，读回后才进入solve，不允许重复案例启动。
    event=ROOT/'outputs/reports'/('entered-'+label+'.json')
    write(event,{'case':label,'input_hashes':read(ROOT/'frozen-inputs.json'),'optimizer_calls':1})
    assert read(event)['optimizer_calls']==1
    tic=time.monotonic()
    meta,sol=kernel.solve(f,x['k'],config['parameters'],cap,flex,peak)
    if sol is None: raise RuntimeError(meta)
    np.savez_compressed(ROOT/'outputs/data'/('reproduced-'+label+'.npz'),**sol)
    write(ROOT/'outputs/reports'/('solver-'+label+'.json'),{'solver':meta,'elapsed_seconds':time.monotonic()-tic})

def run():
    tic=time.monotonic();config,x,price=inputs()
    out=ROOT/'outputs/reports'
    assert not (out/'preflight.json').exists(), '该包仅允许一次四案例运行；不覆盖或重试'
    import scipy
    peak=float((x['observed'].sum(axis=1)+x['aux']-x['pv']).max())
    write(out/'preflight.json',{'planned_optimizer_calls':4,'entered_optimizer_calls_before':0,
          'input_hashes':read(ROOT/'frozen-inputs.json'),'python':sys.version,'executable':sys.executable,
          'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,
          'platform':platform.platform(),'machine':platform.machine(),
          'hard_timeout_per_child_s':30,'supervision_limit_s':180,'shared_peak_MW':peak})
    old={r['case']:r for r in read(ROOT/'saved-cases.json')}
    saved=[];reproduced=[];failure=None
    try:
        for label,cap,flex in CASES:
            item=audit(nz(ROOT/'data/input'/('saved-'+label+'.npz')),x,price,config['parameters'],cap,flex,peak,config['fee_CNY_per_MWh'])
            item.update(case=label,saved_cost_difference_CNY=item['energy_charge_CNY']-old[label]['energy_charge_CNY'])
            assert abs(item['saved_cost_difference_CNY'])<.001
            saved.append(item)
        write(out/'saved-independent-audit.json',saved)
        for label,cap,flex in CASES:
            remaining=180-(time.monotonic()-tic)
            if remaining<=0:raise TimeoutError('总监督时间已达180秒')
            proc=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--child',label],cwd=ROOT,
                    capture_output=True,text=True,timeout=min(30,remaining))
            if proc.returncode:raise RuntimeError({'case':label,'stdout':proc.stdout,'stderr':proc.stderr})
            item=audit(nz(ROOT/'outputs/data'/('reproduced-'+label+'.npz')),x,price,config['parameters'],cap,flex,peak,config['fee_CNY_per_MWh'])
            item.update(case=label,saved_cost_difference_CNY=item['energy_charge_CNY']-old[label]['energy_charge_CNY'])
            assert abs(item['saved_cost_difference_CNY'])<.001,item
            reproduced.append(item)
    except Exception:
        failure=traceback.format_exc()
    # 完整计数反映实际已进入调用边界；进程启动或copy不当作求解完成。
    summary={'status':'PASS_ONE_WINDOW_ONLY' if len(reproduced)==4 and not failure else 'INCOMPLETE',
             'optimizer_calls_entered':len(list(out.glob('entered-*.json'))),
             'reproduced_cases_verified':len(reproduced),'saved_cases_audited':len(saved),
             'start':config['start'],'hours':168,'elapsed_seconds':time.monotonic()-tic,
             'new_cases':reproduced,'failure':failure,
             'max_cost_difference_CNY':max([abs(r['saved_cost_difference_CNY']) for r in reproduced],default=None),
             'max_constraint_residual':max([max(r['errors'].values()) for r in reproduced],default=None),
             'scope':'single frozen window; algebraic feasibility and objective regression only; not annual recomputation or empirical validation'}
    write(out/'run-summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if failure:raise SystemExit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--child', choices=[case[0] for case in CASES])
    args = parser.parse_args()
    # 只在新运行目录建立输出目录；旧结果的独占保护保持原样。
    for folder in ('outputs/reports', 'outputs/data'):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    if args.child:
        child(args.child)
    else:
        run()
