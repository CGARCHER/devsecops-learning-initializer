const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const test=require('node:test');
const path=require('node:path');
const workflow=fs.readFileSync(path.join(__dirname,'../engine/workflows/deploy-dokploy.yml'),'utf8').replace(/\r\n/g,'\n');
const condition=workflow.match(/authorize:\s*#[^\n]*\n\s*if: >-\n([\s\S]*?)\n    uses:/)[1].trim();
function enabled({flag='true',event='workflow_run',branch='main',source='owner/repo',conclusion='success',trigger='push',ref='refs/heads/main'}={}){
 return vm.runInNewContext(condition,{vars:{DOKPLOY_DEPLOY_ENABLED:flag},github:{event_name:event,ref,repository:'owner/repo',event:{workflow_run:{conclusion,head_branch:branch,event:trigger,head_repository:{full_name:source}}}}});
}
test('solo main autorizado puede iniciar la integracion habilitada',()=>{
 assert.equal(enabled(),true);
 assert.equal(enabled({event:'workflow_dispatch'}),true);
 for(const options of [{flag:''},{flag:'false'},{branch:'develop'},{source:'fork/repo'},{conclusion:'failure'},{trigger:'pull_request'},{trigger:'schedule'},{event:'workflow_dispatch',ref:'refs/heads/develop'}])assert.equal(enabled(options),false);
});

