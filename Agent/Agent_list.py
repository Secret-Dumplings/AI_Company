agent_list = {}

def register_agent(uuid, name):
    def _decorator(cls):
        agent_list[uuid] = cls
        agent_list[name] = cls
        return cls
    return _decorator


if __name__ == '__main__':
    # 2. 用法示例
    @register_agent('foo', 'bar')
    class Demo:
        def __init__(self, name):
            self.name = name

        def greet(self):
            return f'Hello {self.name}'

    # 3. 通过任意键都能拿到类
    Cls1 = agent_list['foo']
    Cls2 = agent_list['bar']
    assert Cls1 is Cls2

    # 4. 像正常类一样用
    obj = Cls1('world')
    print(obj.greet())               # Hello world