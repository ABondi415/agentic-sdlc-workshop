"""Project only fixed booleans from native call records; never export payloads."""
import json,sqlite3,sys
from pathlib import Path

def audit(runtime,workspace):
    workspace=Path(workspace).resolve();runtime=Path(runtime).resolve()
    flags={name:False for name in ('saw_read','saw_search','saw_edit','saw_write','saw_exec','saw_delegation','saw_unknown','saw_terminal_command','saw_opaque_native_tool','outside_workspace','control_file_write','has_calls')}
    databases=list(runtime.glob('ap-chat-data-*/chat.db'))
    if not databases:raise ValueError('Missing native call audit database')
    for database in databases:
        if database.is_symlink() or not database.resolve().is_relative_to(runtime):raise ValueError('Unsafe audit database')
        connection=sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)
        try:
            for kind,payload in connection.execute('SELECT type,data FROM conversation_items WHERE type IN (2,7,11)'):
                if kind==11:flags['saw_terminal_command']=True;continue
                if kind==7:flags['saw_opaque_native_tool']=True;continue
                flags['has_calls']=True
                call=json.loads(payload);name=call.get('name');arguments=call.get('arguments')
                if isinstance(arguments,str):arguments=json.loads(arguments)
                if not isinstance(arguments,dict):flags['saw_unknown']=True;continue
                if name not in ('Read','Glob','Grep','Edit','Write'):
                    flags['saw_exec']|=name in ('Bash','PowerShell','sys_os_shell','sys_os_python','sys_os_apply_patch')
                    flags['saw_delegation']|=name in ('Agent','Task','Skill','sys_session_send','sys_session_create')
                    flags['saw_unknown']=True;continue
                flags[{'Read':'saw_read','Glob':'saw_search','Grep':'saw_search','Edit':'saw_edit','Write':'saw_write'}[name]]=True
                raw=arguments.get('file_path') if name in ('Read','Edit','Write') else arguments.get('path','.')
                if not isinstance(raw,str) or not raw:flags['outside_workspace']=True;continue
                path=(workspace/raw).resolve()
                if not path.is_relative_to(workspace):flags['outside_workspace']=True;continue
                relative=path.relative_to(workspace)
                if name in ('Edit','Write') and any(part in ('.git','.github','.claude','.omnigent','.mcp.json') for part in relative.parts):flags['control_file_write']=True
                if name=='Glob':
                    pattern=arguments.get('pattern')
                    if not isinstance(pattern,str) or Path(pattern).is_absolute() or '..' in Path(pattern).parts:flags['outside_workspace']=True
        finally:connection.close()
    passed=(flags['has_calls'] and (flags['saw_edit'] or flags['saw_write']) and not any(flags[k] for k in ('saw_exec','saw_delegation','saw_unknown','saw_terminal_command','saw_opaque_native_tool','outside_workspace','control_file_write')))
    return flags,passed

if __name__=='__main__':
    try:flags,passed=audit(sys.argv[1],sys.argv[2])
    except Exception:
        print(json.dumps({'repair_tool_audit_unavailable':True}));raise SystemExit(1)
    print(json.dumps({'repair_tool_audit':flags,'recorded_static_editing_only':passed},sort_keys=True))
    raise SystemExit(0 if passed else 1)
