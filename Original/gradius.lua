--local memori = string.format(memory.readbyte(0x0020));   É ASSIMMMMMMMMMMMMMMMM PORRAAAAAAA

-- ========================
--    VARIAVEIS 
-- ========================

pipe_out_path   = ("/home/alan/Aula/TCC/pipeout");
pipe_in_path    = ("/home/alan/Aula/TCC/pipein");
pipe_in         = nil;
pipe_out        = nil;
commands        = {};
commands_rcvd   = 0;
x_pos           = 0;
y_pos           = 0;
is_alive        = 0;
framecount      = 0;
positions       = "";

-- ========================
--    POSIÇÕES DE MEMÓRIA 
-- ========================

mem_btpress = 0x0007;  -- botão pressionado (?)
mem_curpos = 0x000F;   -- posição do cursor no menu
mem_paused = 0x0015;   -- 0 = não, 1 = sim
mem_lifes = 0x0020;    -- 3 vidas, 255 = acabou
mem_speed = 0x0040;    -- velocidade da nave
mem_missels = 0x0041;  -- misseis disponíveis
mem_powerbar = 0x0042; -- posição da barra de poder
mem_weaptype = 0x0044; -- tipo de arma
mem_opt = 0x0045;      -- número de opções, sempre manter em 2
mem_transtime = 0x004C;-- tempo para transição de tela
mem_eneload = 0x0060;  -- inimigo carregando ? 2 = carregando 0 = personagem morto????
mem_isalive = 0x0100;  -- 1 = vivo, 2 = morto
mem_xpos = 0x07B7;     -- posição x  (é 0x07A0 - 0X07B7, verificar se não é o tamanho da nave)
mem_ypos = 0x07C7;     -- posição y  (é 0x07B0 - 0X07C7, verificar se não é o tamanho da nave)
mem_score1 = 0x07E4    -- menor digito da pontuação
mem_score2 = 0x07E5    -- digito do meio da pontuação
mem_score3 = 0x07E6    -- maior digito da pontuação

-- ========================
--         FUNÇÕES 
-- ========================

function split(self, delimiter)
    local results = {};
    local start = 1;
    local split_start, split_end  = string.find(self, delimiter, start);
    while split_start do
        table.insert(results, string.sub(self, start, split_start - 1));
        start = split_end + 1;
        split_start, split_end = string.find(self, delimiter, start);
    end;
    table.insert(results, string.sub(self, start));
    return results;
end;

function reset_vars()
    local commands_var = { "up", "left", "down", "right", "A", "B", "start", "select" };
    for i=1,#commands_var do
        commands[commands_var[i]] = false;
    end;
    pipe_in         = nil;
    pipe_out        = nil;
    commands        = {};
    commands_rcvd   = 0;
    x_pos           = 0;
    y_pos           = 0;
    is_alive        = 0;
    framecount      = 0;
    positions       = "";
    close_pipes();
end;

function open_pipes()
    --print("open");
    local _;

    pipe_in, _, _ = io.open(pipe_out_path, "r");
    return;
end;

function close_pipes()
    --print("close");
    if pipe_in then
        pipe_in:close();
    end;
--    if pipe_out then
--        pipe_out:close();
--    end;
    return;
end;

function read_commands()
    if not pipe_in then
        open_pipes()
    end;
    
    local is_received = 0;
    local line = "";
    local line = pipe_in:read();
    --print("Lua recebeu: " .. line);
    if line ~= nil then
        parse_commads(line);
    end;
    return;
end;

--Exemplo de comando inicial 1234#cc#1,0,1,0,1,0
--                           1235#np
-- parts = {"1234", "cc", "1,0"}
function parse_commads(line)
    local parts = split(line, "#");
    local frame_number = parts[1] or "";
    local command = parts[2] or "";
    

    if ("cc" == command) and (tonumber(frame_number) > emu.framecount()) then
        commands_rcvd = 1;
        local controls = split(parts[3], ",");
        commands["up"] =     ((controls[1] == "1") or (controls[1] == "true"));
        commands["down"] =   ((controls[2] == "1") or (controls[2] == "true"));
        commands["left"] =   ((controls[3] == "1") or (controls[3] == "true"));
        commands["right"] =  ((controls[4] == "1") or (controls[4] == "true"));
        commands["A"] =      ((controls[5] == "1") or (controls[5] == "true"));
        commands["B"] =      ((controls[6] == "1") or (controls[6] == "true"));
        commands["start"] =  ((controls[7] == "1") or (controls[6] == "true"));
        commands["select"] = ((controls[8] == "1") or (controls[6] == "true"));
        joypad.set(1, commands);
    elseif ("np" == command) and (tonumber(frame_number) > emu.framecount()) then
        commands["up"] = false;
        commands["down"] = false;
        commands["left"] = false;
        commands["right"] = false;
        commands["A"] = false;
        commands["B"] = false;
        commands["start"] = false;
        commands["select"] = false;
        joypad.set(1, commands);
    elseif "re" == command then
        reset_vars();
        if(emu.framecount() > 10) then
            emu.softreset();
        end;
    end;
    return;
end;

function send_data()
    local data = get_data();
    write_to_pipe(data)
    return;
end;

function write_to_pipe(data)
    pipe_out, _, _ = io.open(pipe_in_path, "w");
    if data and pipe_out then
        pipe_out:write(data);
        pipe_out:flush();
        pipe_out:close();
    end;
    return;
end;

function get_data ()
    local data = ""
    framecount = emu.framecount();
    x_pos = string.format(memory.readbyte(mem_xpos));
    y_pos = string.format(memory.readbyte(mem_ypos));
    is_alive = string.format(memory.readbyte(mem_isalive));
    positions = get_positions();
    data = data .. framecount .. "#";
    data = data .. x_pos .. "," .. y_pos .. "#";
    data = data .. is_alive .. "#";
    data = data .. positions;
    return data;
end;

function get_positions ()
    stringpos = "";
    for i=7,31 do
        id = memory.readbyte(0x0300+i);
        x = memory.readbyte(0x0360+i);
        y = memory.readbyte(0x0320+i);
        if(i > 28) then
            id = 999
        end
        --gui.text(x, y, string.format(id) .. " " .. string.format(i));
        stringpos = stringpos .. string.format(id) .. ","; -- ID
        stringpos = stringpos .. string.format(x) .. ","; -- X
        stringpos = stringpos .. string.format(y) .. "!"; -- Y
        
    end;
    return stringpos;
end;

--reset_vars();
open_pipes();
emu.speedmode("maximum");

while(true) do
    read_commands();
    emu.frameadvance();
    send_data();
end;
