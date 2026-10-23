import {WorkerEntrypoint} from 'cloudflare:workers';
import worker from './worker.mjs';
import {runEvaluationCase} from './evaluation.mjs';
export {MufidGuard} from './worker.mjs';
export default worker;
// This is not an HTTP route. Only a configured Service Binding in this account can call it.
export class MufidEvaluation extends WorkerEntrypoint {
 async runCase(id){return runEvaluationCase(this.env,id);}
}
