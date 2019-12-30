import asyncio


async def func(x):
	await asyncio.sleep(1)
	return x*x

async def main():

	done = await asyncio.gather(*[func(x) for x in range(7)])
	for i in done:
		print(i)


asyncio.run(main())