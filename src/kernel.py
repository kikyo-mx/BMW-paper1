# 原科学函数逐字提取；仅替换导入接线，不修改求解方程。

import numpy as np

import pandas as pd

from scipy.optimize import milp, Bounds, LinearConstraint

from scipy.sparse import coo_matrix

SHOPS=['press','body','paint','assembly']

COLS=['Ele_Press_MWh','Ele_Body_MWh','Ele_Paint_MWh','Ele_AssyLog_MWh']

BUFFERS=['press_body','body_paint','paint_assembly']

CAPS=np.array([606.,20.,116.])

def validate(frame):
    t=pd.DatetimeIndex(pd.to_datetime(frame.timestamp))
    if not len(t) or t.hasnans or t.tz is not None or not t.is_unique:
        raise ValueError('窗口时间键为空、重复、缺失或时区不统一')
    if len(t)%24 or t[0].hour!=6 or not t.equals(pd.date_range(t[0],periods=len(t),freq='h')):
        raise ValueError('窗口须从06:00起连续覆盖完整生产日')
    if any(not isinstance(x,(bool,np.bool_)) for x in frame.energy_usable) or not frame.energy_usable.all():
        raise ValueError('窗口包含无效电量，不能删行或填零')
    names=COLS+['Ele_NonProduction_MWh','Ele_PV_Generation_MWh','Ele_Plant_Total_MWh','price']+[f'{s}_vehicle' for s in SHOPS]+[f'{b}_{pos}_vehicle' for b in BUFFERS for pos in ['start','end']]
    a=frame[names].to_numpy(float)
    if not np.isfinite(a).all():raise ValueError('模型输入含缺失或无穷')
    if (frame[COLS+['Ele_NonProduction_MWh','Ele_PV_Generation_MWh']].to_numpy()<0).any():
        raise ValueError('负电量不能进入映射')
    if np.max(np.abs(frame[COLS].sum(axis=1)+frame.Ele_NonProduction_MWh-frame.Ele_Plant_Total_MWh))>1e-7:
        raise ValueError('分项电量与Total不闭合')

def loads(frame,q,k):
    qref=frame[[f'{s}_vehicle' for s in SHOPS]].to_numpy(float)
    return frame[COLS].to_numpy(float)+(q-qref)*k

def validate_parameters(p,capacity):
    vals=[capacity]+[p[x] for x in ['power_ratio_per_h','roundtrip_efficiency','soc_min','soc_max','soc_initial','daily_discharge_ratio','production_radius','energy_radius']]
    if not np.isfinite(vals).all() or capacity<0 or p['power_ratio_per_h']<0 or p['daily_discharge_ratio']<0:raise ValueError('容量、功率或参数非法')
    if not 0<p['roundtrip_efficiency']<=1 or not 0<=p['soc_min']<=p['soc_initial']<=p['soc_max']<=1:raise ValueError('效率或荷电状态越界')
    if not 0<=p['production_radius']<=1 or not 0<=p['energy_radius']<1:raise ValueError('局部响应范围非法')

def solve(frame,k,p,capacity,flexible,peak_limit_MW=None):
    validate(frame);validate_parameters(p,capacity)
    if peak_limit_MW is not None and (not np.isfinite(peak_limit_MW) or peak_limit_MW<0):
        raise ValueError('峰值上限须为非负有限MW值')
    k=np.asarray(k,float)
    if k.shape!=(4,) or not np.isfinite(k).all() or k.min()<0 or np.any(k[[0,3]]):raise ValueError('响应系数非法')
    n=len(frame);q0=frame[[f'{s}_vehicle' for s in SHOPS]].to_numpy(float);obs=frame[COLS].to_numpy(float)
    starts=frame[[f'{b}_start_vehicle' for b in BUFFERS]].to_numpy(float);ends=frame[[f'{b}_end_vehicle' for b in BUFFERS]].to_numpy(float)
    active=np.repeat(q0[:,3].reshape(-1,24).sum(axis=1)>1e-8,24);available=active & (np.arange(n)%24<20)
    cap=available[:,None]*[120.,70.,70.]
    if max(-q0.min(),(q0[:,:3]-cap).max(),abs(starts[1:]-ends[:-1]).max(),abs(ends-starts-q0[:,:3]+q0[:,1:]).max())>1e-6:raise ValueError('参考生产约束未满足')
    if max(-starts.min(),-ends.min(),(starts-CAPS).max(),(ends-CAPS).max())>1e-6:raise ValueError('参考库存越界')
    aux=frame.Ele_NonProduction_MWh.to_numpy();pv=frame.Ele_PV_Generation_MWh.to_numpy()
    offset=obs-k*q0;grid0=obs.sum(axis=1)+aux-pv
    if grid0.min()<-1e-7:raise ValueError('观测参考无法吸收光伏')
    qid=np.arange(3*n).reshape(n,3);iid=3*n+np.arange(3*(n+1)).reshape(n+1,3)
    idx=6*n+3;gid=np.arange(idx,idx+n);idx+=n;cid=np.arange(idx,idx+n);idx+=n
    did=np.arange(idx,idx+n);idx+=n;sid=np.arange(idx,idx+n+1);idx+=n+1
    zid=np.arange(idx,idx+n);nv=idx+n
    lo=np.zeros(nv);hi=np.full(nv,np.inf);power=capacity*p['power_ratio_per_h']
    # dt=1 h，槽购电量MWh的数值等于该小时平均功率MW。
    # 上限是同窗原固定生产、无电池的最大小时购电功率，不是逐小时原负荷。
    if peak_limit_MW is not None:hi[gid]=float(peak_limit_MW)
    for t in range(n):
        for s in range(3):
            j=qid[t,s]
            if s==0 or not flexible:lo[j]=hi[j]=q0[t,s];continue
            low=max(0.,q0[t,s]-70*p['production_radius']);high=min(cap[t,s],q0[t,s]+70*p['production_radius'])
            if k[s]>0:
                low=max(low,-offset[t,s]/k[s],q0[t,s]-p['energy_radius']*obs[t,s]/k[s])
                high=min(high,q0[t,s]+p['energy_radius']*obs[t,s]/k[s])
            if low>high+1e-7:raise ValueError('局部映射界限与产能冲突')
            lo[j]=low;hi[j]=high
    hi[iid]=CAPS;hi[cid]=hi[did]=power;lo[sid]=capacity*p['soc_min'];hi[sid]=capacity*p['soc_max'];hi[zid]=1 if capacity>0 else 0
    rr=[];cc=[];vv=[];lb=[];ub=[]
    def add(terms,l,u=None):
        row=len(lb)
        for col,val in terms:rr.append(row);cc.append(int(col));vv.append(float(val))
        lb.append(float(l));ub.append(float(l if u is None else u))
    for t in range(n):
        for s in range(3):
            terms=[(iid[t+1,s],1),(iid[t,s],-1),(qid[t,s],-1)]
            if s<2:terms.append((qid[t,s+1],1))
            add(terms,-q0[t,3] if s==2 else 0.)
    for s in range(3):add([(iid[0,s],1)],starts[0,s]);add([(iid[-1,s],1)],ends[-1,s])
    eta=np.sqrt(p['roundtrip_efficiency'])
    for t in range(n):
        # 总平衡保留全部PV；无出口、无弃光。PV可直接用或在TX储能中存储。
        add([(gid[t],1),(cid[t],-1),(did[t],1)]+[(qid[t,s],-k[s]) for s in range(3)],offset[t].sum()+aux[t]-pv[t])
        add([(sid[t+1],1),(sid[t],-1),(cid[t],-eta),(did[t],1/eta)],0.)
        add([(cid[t],1),(zid[t],-power)],-np.inf,0.)
        add([(did[t],1),(zid[t],power)],-np.inf,power)
    add([(sid[0],1)],capacity*p['soc_initial']);add([(sid[-1],1)],capacity*p['soc_initial'])
    for day in range(n//24):add([(did[t],1) for t in range(day*24,(day+1)*24)],-np.inf,capacity*p['daily_discharge_ratio'])
    mat=coo_matrix((vv,(rr,cc)),shape=(len(lb),nv)).tocsc()
    c=np.zeros(nv);c[gid]=frame.price.to_numpy()*1000;integrality=np.zeros(nv,np.int32)
    if capacity>0:integrality[zid]=1
    result=milp(c,integrality=integrality,bounds=Bounds(lo,hi),constraints=LinearConstraint(mat,lb,ub),
        options={'time_limit':p['time_limit_s'],'mip_rel_gap':p['mip_rel_gap']})
    meta={'status':int(result.status),'success':bool(result.success),'message':result.message}
    for key in ['mip_gap','mip_node_count','mip_dual_bound','fun']:
        value=getattr(result,key,None)
        if value is not None and np.isfinite(value):meta[key]=float(value)
    if not result.success:return meta,None
    x=result.x;q=np.column_stack([x[qid],q0[:,3]])
    return meta,{'q':q,'inventory':x[iid],'shop_load_MWh':loads(frame,q,k),'grid_MWh':x[gid],
        'charge_MWh':x[cid],'discharge_MWh':x[did],'soc_MWh':x[sid],'charge_mode':x[zid],'k':k}
