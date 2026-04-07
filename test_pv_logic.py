from easunpy.async_isolar import AsyncISolar
from easunpy.models import PVData
import asyncio

async def test_pv_data_creation():
    # Mock AsyncISolar
    isolar = AsyncISolar("1.2.3.4", "1.2.3.5")
    
    # Values with ONLY temperature
    values = {"pv_temperature": 25}
    pv_data = isolar._create_pv_data(values)
    
    print(f"PV Data with only temperature: {pv_data}")
    assert pv_data is not None
    assert pv_data.temperature == 25
    
    # Values with other PV data
    values = {"pv_total_power": 100, "pv_temperature": 30}
    pv_data = isolar._create_pv_data(values)
    print(f"PV Data with power and temperature: {pv_data}")
    assert pv_data is not None
    assert pv_data.total_power == 100
    assert pv_data.temperature == 30

    print("Verification successful!")

if __name__ == "__main__":
    asyncio.run(test_pv_data_creation())
