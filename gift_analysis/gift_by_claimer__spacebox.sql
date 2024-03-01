SELECT *
FROM (SELECT signer,
             groupArrayIf(passport_nickname, passport_nickname != '')                        as passport_nicknames,
             uniqExactIf(proof_address, proof_address != '')                                 as proof_addresses,
             uniqExactIf(remove_address, remove_address != '')                               as remove_addresses,
             uniqExactIf(gift_claiming_address, gift_claiming_address != '')                 as claim_addresses,
             uniqExactIf(release_address, release_address != '')                             as release_addresses,
             round(sum(gift_amount_gboot), 1)                                                as claim_gboot,
             round(sumIf(gift_amount_gboot, startsWith(gift_claiming_address, '0x')), 1)     as claim_eth_gboot,
             round(sumIf(gift_amount_gboot, startsWith(gift_claiming_address, 'cosmos')), 1) as claim_cosmos_gboot,
             round(sumIf(gift_amount_gboot, startsWith(gift_claiming_address, 'osmo')), 1)   as claim_osmosis_gboot,
             round(sumIf(gift_amount_gboot, startsWith(gift_claiming_address, 'terra')), 1)  as claim_terra_gboot,
             claim_gboot * 0.34 - release_gboot                                              as releasable_gboot,
             round(sum(released_gboot), 1)                                                   as release_gboot
      FROM (SELECT signer,
                   arrayZip(JSONExtractArrayRaw(messages), JSONExtractArrayRaw(raw_log)) as messages_logs_zip,
                   arrayJoin(messages_logs_zip)                                          as message_log_tuple,
                   message_log_tuple.1                                                   as message_row,
                   message_log_tuple.2                                                   as raw_log_item,
                   trim(BOTH '"' FROM
                        replaceAll(replaceAll(message_row, '\\', ''), '@', ''))          as message,
                   JSONExtractString(message, 'type')                                    as message_type,
                   JSONExtractString(message, 'sender')                                  as message_sender,
                   JSONExtractString(message, 'contract')                                as message_contract,
                   JSONExtractString(message, 'msg')                                     as message_msg,
                   JSON_VALUE(message_msg, '$.create_passport.nickname')                 as passport_nickname,
                   JSON_VALUE(message_msg, '$.proof_address.address')                    as proof_address,
                   JSON_VALUE(message_msg, '$.remove_address.address')                   as remove_address,
                   JSON_VALUE(message_msg, '$.release.gift_address')                     as release_address,
                   round(toInt64OrZero(JSON_VALUE(message_msg, '$.claim.gift_amount')) / 1e9,
                         1)                                                              as gift_amount_raw_gboot,
                   JSON_VALUE(message_msg, '$.claim.gift_claiming_address')              as gift_claiming_address,
                   toInt64OrZero(replace(
                           JSON_VALUE(raw_log_item, '$.events[1].attributes[0].value'),
                           'boot', '')) /
                   1e9                                                                   as released_gboot,
                   toInt64OrZero(JSON_VALUE(raw_log_item, '$.events[5].attributes[4].value')) /
                   1e9                                                                   as gift_amount_gboot,
                   date
            FROM (SELECT height,
                         signer,
                         raw_log,
                         messages,
                         date
                  FROM `spacebox`.transaction FINAL
                           LEFT ANY
                           JOIN (
                      SELECT height,
                             toDate(timestamp) as date
                      FROM `spacebox`.block
                          PREWHERE block.height > 10800000
                      ) as b
                                ON transaction.height = b.height
                      PREWHERE transaction.success = true
                      and transaction.height > 10800000
                     )
            WHERE message_type == '/cosmwasm.wasm.v1.MsgExecuteContract'
              and message_contract in ('bostrom1xut80d09q0tgtch8p0z4k5f88d3uvt8cvtzm5h3tu3tsy4jk9xlsfzhxel',
                                       'bostrom16t6tucgcqdmegye6c9ltlkr237z8yfndmasrhvh7ucrfuqaev6xq7cpvek')
            ORDER BY height DESC)
      GROUP BY signer)
-- WHERE release_gboot > 0
ORDER BY release_gboot DESC;
