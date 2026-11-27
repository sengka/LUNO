export function CapacityValue({points}:{points:number|null}) {
 return <span>{points===null?'Kapasite tanımsız':`${points} puan`}</span>
}
