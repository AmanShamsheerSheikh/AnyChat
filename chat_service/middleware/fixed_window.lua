local key = KEYS[1]
local limit = tonumber(ARGV[1])
local duration = tonumber(ARGV[2])
local counter = redis.call('GET', key)
if counter == false then
    redis.call('SETEX', key, duration, 1)
    return 1
end
if tonumber(counter) >= limit then
    return 0
end
redis.call('INCR', key)
return 1